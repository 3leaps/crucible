#!/usr/bin/env python3
"""Draft shape, vocabulary parity and necessary-condition controls; no crypto."""

import copy
import datetime
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
FAMILY = ROOT / "schemas/identity-evidence/v0"
DIMENSIONS = (
    "identity-binding",
    "key-custody",
    "execution-isolation",
    "platform-evidence",
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def instant(value):
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def json_equal(left, right):
    """Compare validated JSON values without Python's bool/number equivalence.

    Object order is immaterial; array order is material. Equal numeric values
    (including 1 and 1.0, or signed zero) remain equal. This is not a JCS encoder
    or a replacement for a property's numeric-domain validation.
    """
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            json_equal(left[k], right[k]) for k in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            json_equal(a, b) for a, b in zip(left, right)
        )
    if type(left) in (int, float) and type(right) in (int, float):
        return left == right
    return type(left) is type(right) and left == right


def fixture_digest(report):
    """JCS-equivalent ONLY for the ASCII, nonnumeric fixture subset used here."""

    def subset(v):
        if isinstance(v, str):
            require(v.isascii(), "fixture-hash-subset")
        elif isinstance(v, dict):
            for k, item in v.items():
                subset(k)
                subset(item)
        elif isinstance(v, list):
            for item in v:
                subset(item)
        else:
            require(v is None or isinstance(v, bool), "fixture-hash-subset")

    subset(report)
    wire = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(wire.encode()).hexdigest()


def boundary_identity(boundary):
    if boundary is None:
        return None
    normalized = copy.deepcopy(boundary)
    for field in ("comparison_subject_refs", "threats"):
        normalized[field] = sorted(normalized[field])
    return json.dumps(normalized, sort_keys=True)


def necessary_conditions(report, input_reports=None):
    """Necessary shape/reference rules, not evidence or evaluator authentication."""
    indexes = {}
    for collection in (
        "subjects",
        "identifiers",
        "keys",
        "claims",
        "evidence",
        "capabilities",
        "input_reports",
    ):
        records = report[collection]
        indexes[collection] = {r["id"]: r for r in records}
        require(len(indexes[collection]) == len(records), "duplicate-reference")
    subjects, identifiers, keys, claims, evidence = (
        indexes[k] for k in ("subjects", "identifiers", "keys", "claims", "evidence")
    )
    # Attribution belongs to one event, never to the record's policy deadline.
    for records, field in (
        ([report], "created_at"),
        (report["evidence"], "collected_at"),
        (report["assessments"], "assessed_at"),
        (report["capabilities"], "observed_at"),
    ):
        for record in records:
            if "time_attribution" in record:
                require(
                    record["time_attribution"]["instant"] == record[field],
                    "time-attribution-instant-mismatch",
                )
    created = instant(report["created_at"])
    for a in report["assessments"]:
        if a["dimension"] == "key-custody" and a["value"] == "not-applicable":
            require("key_ref" not in a, "not-applicable-custody-has-key")
    for collection in (
        "identifiers",
        "keys",
        "claims",
        "evidence",
        "assessments",
        "capabilities",
    ):
        for r in report[collection]:
            require(r["subject_ref"] in subjects, "unknown-subject")
            for field, index in (("identifier_ref", identifiers), ("key_ref", keys)):
                if field in r:
                    item = index.get(r[field])
                    require(
                        item is not None and item["subject_ref"] == r["subject_ref"],
                        field + "-subject-mismatch",
                    )
            for cr in r.get("claim_refs", []):
                c = claims.get(cr)
                require(
                    c is not None and c["subject_ref"] == r["subject_ref"],
                    "claim-subject-mismatch",
                )
                if "key_ref" in c and collection == "evidence":
                    require(c["key_ref"] == r.get("key_ref"), "claim-key-mismatch")
            if "boundary" in r:
                require(
                    all(
                        x in subjects and x != r["subject_ref"]
                        for x in r["boundary"]["comparison_subject_refs"]
                    ),
                    "invalid-comparison-subject",
                )
    for e in evidence.values():
        require(instant(e["collected_at"]) <= created, "future-evidence")
    for c in report["capabilities"]:
        require(instant(c["observed_at"]) <= created, "future-capability")
    resolved = {}
    for source in report["input_reports"]:
        original = (input_reports or {}).get(source["report_id"])
        require(original is not None, "input-report-unavailable")
        require(
            original.get("report_id") == source["report_id"], "input-report-id-mismatch"
        )
        require(
            fixture_digest(original) == source["digest"], "input-report-digest-mismatch"
        )
        require(
            source["report_id"] != report["report_id"]
            and instant(original["created_at"]) <= created,
            "invalid-input-report",
        )
        resolved[source["id"]] = original
    for collection in ("evidence", "capabilities"):
        for r in report[collection]:
            if "origin" not in r:
                continue
            origin = r["origin"]
            source = resolved.get(origin["input_ref"])
            require(source is not None, "unknown-input-report")
            old = next(
                (x for x in source[collection] if x["id"] == origin["record_ref"]), None
            )
            stripped = {k: v for k, v in r.items() if k != "origin"}
            old_stripped = {k: v for k, v in (old or {}).items() if k != "origin"}
            require(
                old is not None and json_equal(stripped, old_stripped),
                "input-observation-changed",
            )
            # v0 preserves referenced local IDs/descriptors when carrying observations forward.
            references = [("subjects", r["subject_ref"])]
            references += [
                (coll, r[field])
                for field, coll in (
                    ("identifier_ref", "identifiers"),
                    ("key_ref", "keys"),
                )
                if field in r
            ]
            references += [("claims", x) for x in r.get("claim_refs", [])]
            references += [
                ("subjects", x)
                for x in r.get("boundary", {}).get("comparison_subject_refs", [])
            ]
            for coll, rid in references:
                old_item = next((x for x in source[coll] if x["id"] == rid), None)
                require(
                    old_item is not None
                    and json_equal(old_item, indexes[coll].get(rid)),
                    "input-reference-changed",
                )
    seen = set()
    for a in report["assessments"]:
        key = (
            a["subject_ref"],
            a.get("identifier_ref"),
            a.get("key_ref"),
            a["dimension"],
            a["scope"],
            boundary_identity(a.get("boundary")),
            tuple(sorted(a.get("claim_refs", []))),
        )
        require(key not in seen, "duplicate-assessment-scope")
        seen.add(key)
        start, end = instant(a["assessed_at"]), instant(a["valid_until"])
        require(start <= created and start < end, "invalid-assessment-window")
        if a["state"] == "current":
            require(created < end, "expired-current-assessment")
        refs = a["evidence_refs"]
        require(all(r in evidence for r in refs), "unknown-evidence")
        es = [evidence[r] for r in refs]
        require(
            all(e["subject_ref"] == a["subject_ref"] for e in es),
            "evidence-subject-mismatch",
        )
        require(
            all(instant(e["collected_at"]) <= start for e in es),
            "evidence-after-assessment",
        )
        dim, value = a["dimension"], a["value"]
        if "key_ref" in a:
            require(
                all(e.get("key_ref") == a["key_ref"] for e in es),
                "evidence-key-mismatch",
            )
        keyed = {
            e["method"]
            for e in es
            if "key_ref" in a and e.get("key_ref") == a["key_ref"]
        }
        named = {
            e["method"]
            for e in es
            if "identifier_ref" in a and e.get("identifier_ref") == a["identifier_ref"]
        }
        if dim == "identity-binding":
            if value == "declared":
                require("declaration" in named, "declaration-required")
            if value == "observed":
                require("os-observation" in named, "observation-required")
            if value == "enrolled-key":
                require(
                    "enrollment" in named
                    and {"enrollment", "possession-proof"} <= keyed,
                    "enrollment-and-proof-required",
                )
            if value == "attested-key":
                require(
                    "possession-proof" in keyed
                    and bool(keyed & {"device-attestation", "workload-attestation"})
                    and bool(named & {"device-attestation", "workload-attestation"}),
                    "attestation-and-proof-required",
                )
        if dim == "key-custody":
            if value in {"software", "os-managed"}:
                require("custody-observation" in keyed, "custody-observation-required")
            if value in {"hardware-backed", "virtual-hardware-backed"}:
                require(
                    bool(
                        keyed
                        & {
                            "device-attestation",
                            "workload-attestation",
                            "custody-observation",
                        }
                    ),
                    "key-custody-evidence-required",
                )
        if dim == "execution-isolation" and value != "unknown":
            matching = {
                e["method"]
                for e in es
                if boundary_identity(e.get("boundary"))
                == boundary_identity(a["boundary"])
            }
            require(
                bool(
                    matching
                    & {
                        "isolation-observation",
                        "workload-attestation",
                        "authority-statement",
                    }
                ),
                "isolation-boundary-evidence-required",
            )
            if value == "confidential-workload":
                require(
                    "workload-attestation" in matching, "workload-attestation-required"
                )
        if dim == "platform-evidence" and value != "unknown":
            expected = {
                "declared": {"declaration"},
                "locally-observed": {"os-observation"},
                "authority-verified": {"authority-statement"},
                "hardware-attested": {"device-attestation", "workload-attestation"},
            }
            for cr in a["claim_refs"]:
                require(
                    any(
                        cr in e.get("claim_refs", []) and e["method"] in expected[value]
                        for e in es
                    ),
                    "platform-claim-evidence-required",
                )


def process_session_fit(report, bundle, context, profile, profile_ref):
    """Contract fit with caller-supplied verifier results; NEVER a crypto verifier."""
    require(bundle["profile"] == profile_ref, "unsupported-evidence-profile")
    process, session, receipt, challenge, proof = (
        bundle[k] for k in ("process", "session", "launch", "challenge", "proof")
    )
    now = instant(context["now"])
    for window, maximum in (
        (receipt, profile["max_receipt_seconds"]),
        (challenge, profile["max_challenge_seconds"]),
    ):
        issued, expires = instant(window["issued_at"]), instant(window["expires_at"])
        require(
            issued < expires
            and (expires - issued).total_seconds() <= maximum
            and (issued - now).total_seconds() <= profile["max_future_skew_seconds"]
            and now < expires,
            "expired-or-invalid-window",
        )
    require(context["process_live"], "process-not-live")
    require(
        0
        <= (now - instant(context["observed_at"])).total_seconds()
        <= profile["max_observation_age_seconds"],
        "stale-process-observation",
    )
    require(
        json_equal(process, context["current_process"]),
        "process-incarnation-or-context-changed",
    )
    require(
        json_equal(session, context["expected_session"]),
        "session-key-or-enrollment-changed",
    )
    subjects = {x["id"]: x for x in report["subjects"]}
    require(
        subjects.get(process["subject_ref"], {}).get("kind") == "process"
        and subjects.get(session["subject_ref"], {}).get("kind") == "session",
        "process-session-subject-mismatch",
    )
    key = next((x for x in report["keys"] if x["id"] == session["key_ref"]), None)
    identifier = next(
        (x for x in report["identifiers"] if x["id"] == session["identifier_ref"]), None
    )
    require(
        key is not None
        and key["subject_ref"] == session["subject_ref"]
        and key["public_key_digest"] == session["public_key_digest"]
        and key["representation_profile"] == session["key_representation_profile"]
        and identifier is not None
        and identifier["subject_ref"] == session["subject_ref"]
        and fixture_digest(identifier) == session["identifier_digest"],
        "report-session-key-mismatch",
    )
    require(
        receipt["process_digest"] == fixture_digest(process)
        and receipt["session_digest"] == fixture_digest(session),
        "receipt-binding-mismatch",
    )
    require(
        receipt["issuer"] == context["accepted_launch_issuer"]
        and receipt["intent_digest"] == context["expected_intent_digest"],
        "launch-intent-or-issuer-mismatch",
    )
    require(
        not any(
            item["issuer"] == receipt["issuer"]
            and item["receipt_id"] == receipt["receipt_id"]
            for item in context["consumed_receipts"]
        ),
        "launch-receipt-replayed",
    )
    require(
        challenge["nonce"] not in context["consumed_challenges"],
        "launch-challenge-replayed",
    )
    receipt_digest = fixture_digest(receipt)
    require(
        receipt_digest == context["verified_receipt_digest"],
        "receipt-verification-binding-mismatch",
    )
    require(challenge["receipt_digest"] == receipt_digest, "challenge-receipt-mismatch")
    require(
        challenge["audience"] == context["audience"]
        and challenge["nonce"] == context["nonce"],
        "challenge-audience-or-nonce-mismatch",
    )
    transcript = {
        "domain": profile["transcript_domain"],
        "profile": profile_ref,
        "process_digest": fixture_digest(process),
        "session_digest": fixture_digest(session),
        "receipt_digest": receipt_digest,
        "challenge": challenge,
    }
    transcript_digest = fixture_digest(transcript)
    require(
        proof["key_ref"] == session["key_ref"]
        and proof["transcript_digest"] == transcript_digest
        and context["verified_transcript_digest"] == transcript_digest
        and context["verified_key_digest"] == key["public_key_digest"]
        and context["verified_proof_digest"] == proof["proof_digest"],
        "possession-verification-binding-mismatch",
    )
    evidence = {x["id"]: x for x in report["evidence"]}
    claims = {x["id"]: x for x in report["claims"]}
    bundle_digest = fixture_digest(bundle)

    def launch_claim_matches(claim):
        return (
            claim["subject_ref"] == process["subject_ref"]
            and claim["property_profile"] == profile_ref
            and claim["property"] == "launch-bound-session"
            and claim["value"] == session["subject_ref"]
            and "key_ref" not in claim
        )

    # Resolve descriptors by pinned format/content, never by fixture-local IDs.
    bound = {}
    for e in evidence.values():
        if e["format_profile"] != profile_ref and e["digest"] != bundle_digest:
            continue
        require(
            e["format_profile"] == profile_ref and e["digest"] == bundle_digest,
            "report-evidence-binding-mismatch",
        )
        if e["method"] == "possession-proof":
            require(
                e["subject_ref"] == session["subject_ref"]
                and e.get("identifier_ref") == session["identifier_ref"]
                and e.get("key_ref") == session["key_ref"]
                and not e.get("claim_refs")
                and "boundary" not in e,
                "report-possession-descriptor-mismatch",
            )
        elif e["method"] == "os-observation":
            require(
                e["subject_ref"] == process["subject_ref"]
                and "identifier_ref" not in e
                and "key_ref" not in e
                and "boundary" not in e,
                "report-process-descriptor-mismatch",
            )
            require(
                bool(e.get("claim_refs"))
                and all(launch_claim_matches(claims[cr]) for cr in e["claim_refs"]),
                "process-session-claim-mismatch",
            )
        else:
            raise ValueError("report-evidence-method-mismatch")
        bound[e["id"]] = e

    used_methods = set()
    for a in report["assessments"]:
        selected = [bound[er] for er in a["evidence_refs"] if er in bound]
        selected_claims = [claims[cr] for cr in a.get("claim_refs", [])]
        if not selected:
            require(
                a["rule"] != profile_ref
                and not any(
                    c["property_profile"] == profile_ref for c in selected_claims
                ),
                "assessment-bundle-evidence-required",
            )
            continue
        for e in selected:
            if e["method"] == "possession-proof":
                require(
                    a["dimension"] == "identity-binding"
                    and a["value"] == "enrolled-key"
                    and a["subject_ref"] == session["subject_ref"]
                    and a.get("identifier_ref") == session["identifier_ref"]
                    and a.get("key_ref") == session["key_ref"],
                    "assessment-possession-binding-mismatch",
                )
            else:
                require(
                    a["dimension"] == "platform-evidence"
                    and a["value"] == "locally-observed"
                    and a["rule"] == profile_ref
                    and a["subject_ref"] == process["subject_ref"]
                    and "identifier_ref" not in a
                    and "key_ref" not in a,
                    "assessment-process-binding-mismatch",
                )
                require(
                    bool(selected_claims)
                    and all(launch_claim_matches(c) for c in selected_claims)
                    and set(a["claim_refs"]).issubset(e["claim_refs"]),
                    "assessment-process-claim-mismatch",
                )
            used_methods.add(e["method"])
    require(
        used_methods == {"possession-proof", "os-observation"},
        "process-session-assessments-required",
    )
    expiry = min(instant(receipt["expires_at"]), instant(challenge["expires_at"]))
    require(
        all(instant(a["valid_until"]) <= expiry for a in report["assessments"]),
        "assessment-outlives-binding",
    )
    require(
        all(now < instant(a["valid_until"]) for a in report["assessments"]),
        "assessment-expired",
    )
    require(
        all(
            a["state"] == "current" and instant(a["assessed_at"]) <= now
            for a in report["assessments"]
        ),
        "assessment-not-current",
    )


def check_import_collisions(reports):
    """No remapping: unequal descriptors sharing a local collection/ID refuse."""
    seen = {}
    for report in reports:
        for collection in (
            "subjects",
            "identifiers",
            "keys",
            "claims",
            "evidence",
            "capabilities",
            "input_reports",
        ):
            for record in report[collection]:
                key = (collection, record["id"])
                require(
                    key not in seen or json_equal(seen[key], record),
                    "import-id-collision",
                )
                seen[key] = record


def main():
    goneat = shutil.which("goneat")
    require(goneat, "goneat is required")
    schema = json.loads((FAMILY / "report.schema.json").read_text())
    with tempfile.TemporaryDirectory(prefix="identity-evidence-controls-") as directory:
        data = Path(directory) / "case.json"

        def shape(instance, schema_path, accepted=True):
            data.write_text(json.dumps(instance))
            result = subprocess.run(
                [
                    goneat,
                    "validate",
                    "data",
                    "--schema-file",
                    str(schema_path),
                    "--data",
                    str(data),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            require(
                (result.returncode == 0) == accepted,
                "shape expectation failed: " + result.stdout + result.stderr,
            )

        # Wire admission vectors are shared data, not outputs captured from an adopter.
        time_example = json.loads(
            (FAMILY / "examples/time-attribution-mixed.json").read_text()
        )
        shape(time_example, FAMILY / "report.schema.json")
        necessary_conditions(time_example)
        time_shapes = []
        r = copy.deepcopy(time_example)
        del r["evidence"][0]["time_attribution"]["evidence"]
        time_shapes.append(r)
        r = copy.deepcopy(time_example)
        del r["evidence"][0]["time_attribution"]["evidence"]["format_profile"]
        time_shapes.append(r)
        r = copy.deepcopy(time_example)
        r["time_attribution"]["evidence"] = r["evidence"][0]["time_attribution"][
            "evidence"
        ]
        time_shapes.append(r)
        r = copy.deepcopy(time_example)
        r["time_attribution"]["source"] = "trusted_by_name"
        time_shapes.append(r)
        r = copy.deepcopy(time_example)
        r["time_attribution"]["instant"] = "2026-10-29T12:00:00.000000Z"
        time_shapes.append(r)
        r = copy.deepcopy(time_example)
        r["assessments"][0]["valid_until_attribution"] = r["time_attribution"]
        time_shapes.append(r)
        for r in time_shapes:
            shape(r, FAMILY / "report.schema.json", accepted=False)
        for collection in (None, "evidence", "assessments", "capabilities"):
            r = copy.deepcopy(time_example)
            target = r if collection is None else r[collection][0]
            target["time_attribution"]["instant"] = "2026-10-29T11:59:59Z"
            shape(r, FAMILY / "report.schema.json")
            try:
                necessary_conditions(r)
            except ValueError as exc:
                require(
                    str(exc) == "time-attribution-instant-mismatch",
                    "wrong-time-refusal",
                )
            else:
                raise ValueError("accepted mismatched event time attribution")

        # Carry-forward retains the complete original time attribution.
        attributed_input = copy.deepcopy(time_example)
        carried = copy.deepcopy(time_example)
        carried["report_id"] = "attributed-later-evaluation"
        carried["input_reports"] = [
            {
                "id": "source-time",
                "report_id": attributed_input["report_id"],
                "digest": fixture_digest(attributed_input),
            }
        ]
        carried["evidence"][0]["origin"] = {
            "input_ref": "source-time",
            "record_ref": carried["evidence"][0]["id"],
        }
        shape(carried, FAMILY / "report.schema.json")
        necessary_conditions(carried, {attributed_input["report_id"]: attributed_input})
        carried["evidence"][0]["time_attribution"]["evidence"]["digest"] = (
            "sha256:" + "0" * 64
        )
        shape(carried, FAMILY / "report.schema.json")
        try:
            necessary_conditions(
                carried, {attributed_input["report_id"]: attributed_input}
            )
        except ValueError as exc:
            require(
                str(exc) == "input-observation-changed",
                "wrong-attribution-import-refusal",
            )
        else:
            raise ValueError("accepted rewritten imported time attribution")

        for dimension in DIMENSIONS:
            config = json.loads(
                (
                    ROOT / f"config/classifiers/dimensions/{dimension}.dimension.json"
                ).read_text()
            )
            shape(
                config, ROOT / "schemas/classifiers/v0/dimension-definition.schema.json"
            )
            values = [v["key"] for v in config["categorical"]["values"]]
            require(values == schema["$defs"][dimension]["enum"], "vocabulary-drift")
            require(
                len(values) == len(set(values)) and "unknown" in values,
                "bad-vocabulary",
            )
            require(
                config["categorical"]["index_strategy"]["missing_handling"] == "error",
                "implicit-default",
            )

        examples = {
            path.stem: json.loads(path.read_text())
            for path in (FAMILY / "examples").glob("*.json")
        }
        report_inputs = {r["report_id"]: r for r in examples.values()}
        for path in sorted((FAMILY / "examples").glob("*.json")):
            r = json.loads(path.read_text())
            shape(r, FAMILY / "report.schema.json")
            necessary_conditions(r, report_inputs)
            examples[path.stem] = r

        baseline = examples["software-enrolled-session"]
        schema_mutations = []
        r = copy.deepcopy(baseline)
        del r["assessments"][0]["value"]
        schema_mutations.append(r)
        r = copy.deepcopy(baseline)
        r["assessments"][0]["value"] = "highest"
        schema_mutations.append(r)
        r = copy.deepcopy(baseline)
        r["capabilities"][0]["status"] = "no-tpm-probably"
        schema_mutations.append(r)
        r = copy.deepcopy(baseline)
        r["private_key"] = "not-a-real-secret"
        schema_mutations.append(r)
        r = copy.deepcopy(baseline)
        del r["assessments"][0]["identifier_ref"]
        schema_mutations.append(r)
        for field in ("key_ref",):
            r = copy.deepcopy(baseline)
            del r["assessments"][0][field]
            schema_mutations.append(r)
        r = copy.deepcopy(baseline)
        del r["evaluator"]
        schema_mutations.append(r)
        r = copy.deepcopy(examples["observation-only-installation"])
        r["evaluator"] = copy.deepcopy(baseline["evaluator"])
        schema_mutations.append(r)
        r = copy.deepcopy(baseline)
        del r["evaluator"]["principal"]
        schema_mutations.append(r)
        r = copy.deepcopy(baseline)
        del r["evaluator"]["verification_profile"]
        schema_mutations.append(r)
        r = copy.deepcopy(examples["shared-account-process"])
        del r["assessments"][0]["boundary"]
        schema_mutations.append(r)
        r = copy.deepcopy(examples["shared-account-process"])
        r["assessments"][0]["boundary"]["comparison_subject_refs"] = []
        schema_mutations.append(r)
        r = copy.deepcopy(examples["attested-key-origin-property"])
        del r["assessments"][-1]["claim_refs"]
        schema_mutations.append(r)
        r = copy.deepcopy(baseline)
        r["assessments"][1].update(value="not-applicable", evidence_refs=[])
        schema_mutations.append(r)
        try:
            necessary_conditions(r)
        except ValueError as exc:
            require(
                str(exc) == "not-applicable-custody-has-key", "wrong-custody-refusal"
            )
        else:
            raise ValueError("accepted not-applicable custody with a key")
        r = copy.deepcopy(examples["observation-only-installation"])
        del r["evidence"][0]["format_profile"]
        schema_mutations.append(r)
        for r in schema_mutations:
            shape(r, FAMILY / "report.schema.json", False)

        semantic_mutations = []
        r = copy.deepcopy(baseline)
        r["assessments"][0]["evidence_refs"] = ["e-pop"]
        semantic_mutations.append((r, "enrollment-and-proof-required"))
        r = copy.deepcopy(baseline)
        r["assessments"][0]["value"] = "attested-key"
        semantic_mutations.append((r, "attestation-and-proof-required"))
        r = copy.deepcopy(baseline)
        r["assessments"][0]["evidence_refs"] = ["missing"]
        semantic_mutations.append((r, "unknown-evidence"))
        r = copy.deepcopy(baseline)
        r["subjects"].append({"id": "issuer", "kind": "key-holder"})
        r["evidence"][0]["subject_ref"] = "issuer"
        del r["evidence"][0]["identifier_ref"]
        del r["evidence"][0]["key_ref"]
        semantic_mutations.append((r, "evidence-subject-mismatch"))
        r = copy.deepcopy(baseline)
        r["created_at"] = "2026-10-29T12:06:00Z"
        semantic_mutations.append((r, "expired-current-assessment"))
        r = copy.deepcopy(baseline)
        r["identifiers"].append(copy.deepcopy(r["identifiers"][0]))
        semantic_mutations.append((r, "duplicate-reference"))
        r = copy.deepcopy(baseline)
        r["assessments"].append(copy.deepcopy(r["assessments"][0]))
        semantic_mutations.append((r, "duplicate-assessment-scope"))
        r = copy.deepcopy(baseline)
        r["assessments"][1]["value"] = "hardware-backed"
        r["assessments"][1]["evidence_refs"] = ["e-enroll"]
        semantic_mutations.append((r, "key-custody-evidence-required"))
        for assessment, old_evidence in ((2, "e-pop"), (3, "e-custody")):
            r = copy.deepcopy(examples["software-key-rotation"])
            r["assessments"][assessment]["evidence_refs"][-1] = old_evidence
            semantic_mutations.append((r, "evidence-key-mismatch"))
        r = copy.deepcopy(examples["software-key-rotation"])
        r["evidence"][-3]["identifier_ref"] = "identifier-other"
        other = copy.deepcopy(r["identifiers"][0])
        other["id"] = "identifier-other"
        other["value"] = "different-enrollment"
        r["identifiers"].append(other)
        semantic_mutations.append((r, "enrollment-and-proof-required"))
        r = copy.deepcopy(examples["shared-account-process"])
        r["assessments"][0]["boundary"]["threats"] = ["different-threat"]
        semantic_mutations.append((r, "isolation-boundary-evidence-required"))
        r = copy.deepcopy(examples["shared-account-process"])
        r["assessments"][0]["subject_ref"] = "neighbor-process"
        r["assessments"][0]["boundary"]["comparison_subject_refs"] = ["subject-a"]
        semantic_mutations.append((r, "evidence-subject-mismatch"))
        r = copy.deepcopy(examples["shared-guest-hardware-issuer"])
        r["assessments"][2]["evidence_refs"] = ["e-guest"]
        semantic_mutations.append((r, "evidence-subject-mismatch"))
        r = copy.deepcopy(examples["attested-key-origin-property"])
        other = copy.deepcopy(r["claims"][0])
        other.update(
            id="claim-os-version", property="os-version", value="synthetic-os-version"
        )
        other.pop("key_ref")
        r["claims"].append(other)
        r["assessments"][-1]["claim_refs"] = ["claim-os-version"]
        semantic_mutations.append((r, "platform-claim-evidence-required"))
        r = copy.deepcopy(examples["attested-key-origin-property"])
        other = copy.deepcopy(r["keys"][0])
        other["id"] = "key-other"
        r["keys"].append(other)
        r["claims"][0]["key_ref"] = "key-other"
        semantic_mutations.append((r, "claim-key-mismatch"))
        r = copy.deepcopy(examples["evaluated-installation"])
        r["evidence"][0]["collected_at"] = "2026-10-29T12:01:00Z"
        semantic_mutations.append((r, "input-observation-changed"))
        r = copy.deepcopy(examples["evaluated-installation"])
        r["identifiers"][0]["value"] = "substituted-installation"
        semantic_mutations.append((r, "input-reference-changed"))
        r = copy.deepcopy(examples["evaluated-installation"])
        r["input_reports"][0]["digest"] = "sha256:" + "0" * 64
        semantic_mutations.append((r, "input-report-digest-mismatch"))
        # Reviewer reproductions: keep source bytes/digest unchanged and mutate
        # only the imported descriptor. Both source and valid target pass first.
        for original, replacement, suffix in ((True, 1, "true"), (False, 0, "false")):
            source = copy.deepcopy(examples["observation-only-installation"])
            source["report_id"] = "observation-boolean-" + suffix
            claim = {
                "id": "claim-flag",
                "subject_ref": "subject-a",
                "property_profile": copy.deepcopy(
                    source["identifiers"][0]["derivation"]
                ),
                "property": "synthetic-flag",
                "value": original,
            }
            source["claims"] = [claim]
            source["evidence"][0]["claim_refs"] = ["claim-flag"]
            shape(source, FAMILY / "report.schema.json")
            necessary_conditions(source)
            report_inputs[source["report_id"]] = source
            r = copy.deepcopy(examples["evaluated-installation"])
            r["claims"] = copy.deepcopy(source["claims"])
            r["evidence"][0]["claim_refs"] = ["claim-flag"]
            r["input_reports"][0].update(
                report_id=source["report_id"], digest=fixture_digest(source)
            )
            shape(r, FAMILY / "report.schema.json")
            necessary_conditions(r, report_inputs)
            r["claims"][0]["value"] = replacement
            semantic_mutations.append((r, "input-reference-changed"))
        r = copy.deepcopy(examples["evaluated-installation"])
        r["input_reports"][0]["report_id"] = "misresolved-report"
        report_inputs["misresolved-report"] = examples["observation-only-installation"]
        semantic_mutations.append((r, "input-report-id-mismatch"))
        # JSON distinguishes booleans from numbers recursively, but not integer
        # and float spellings of the same supported numeric value.
        require(json_equal({"a": [1, -0.0]}, {"a": [1.0, 0]}), "numeric-equality-lost")
        require(not json_equal({"a": [True]}, {"a": [1]}), "nested-boolean-equality")
        require(not json_equal([False], [0]), "nested-false-equality")
        require(not json_equal([1, 2], [2, 1]), "array-order-lost")
        require(
            json_equal({"a": 1, "b": 2}, {"b": 2.0, "a": 1.0}),
            "object-order-changed-equality",
        )
        for r, error in semantic_mutations:
            shape(r, FAMILY / "report.schema.json")
            try:
                necessary_conditions(r, report_inputs)
            except ValueError as exc:
                require(str(exc) == error, f"wrong refusal: {exc}; expected {error}")
            else:
                raise ValueError(f"accepted negative control: {error}")

        process_root = FAMILY / "profiles/local-process-session"
        profile_path = process_root / "profile.json"
        profile = json.loads(profile_path.read_text())
        profile_ref = {
            "id": profile["id"],
            "revision": "sha256:"
            + hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        }
        require(
            profile["evidence_schema"]["revision"]
            == "sha256:"
            + hashlib.sha256(
                (process_root / "evidence.schema.json").read_bytes()
            ).hexdigest(),
            "process-schema-pin-drift",
        )
        require(
            profile["specification"]["revision"]
            == "sha256:"
            + hashlib.sha256((process_root / "README.md").read_bytes()).hexdigest(),
            "process-specification-pin-drift",
        )
        bundle = json.loads((process_root / "evidence.example.json").read_text())
        shape(bundle, process_root / "evidence.schema.json")
        original_context = json.loads(
            (process_root / "evaluation-context.example.json").read_text()
        )
        process_cases = json.loads((process_root / "cases.json").read_text())
        process_cases += json.loads((process_root / "report-cases.json").read_text())
        for case in process_cases:
            context = copy.deepcopy(original_context)
            report = copy.deepcopy(examples["local-process-session-launch"])
            original_report = copy.deepcopy(report)
            context_changes = case.get("context_changes", [])
            if case.get("change"):
                context_changes = [case["change"]] + context_changes
            for document, changes in (
                (context, context_changes),
                (report, case.get("report_changes", [])),
                (original_report, case.get("input_report_changes", [])),
            ):
                for change in changes:
                    target = document
                    for part in change["path"][:-1]:
                        target = target[part]
                    leaf = change["path"][-1]
                    if leaf == "-":
                        target.append(copy.deepcopy(change["value"]))
                    else:
                        target[leaf] = copy.deepcopy(change["value"])
            # These vectors must reach the fit boundary with valid report shape
            # and necessary conditions, rather than fail in an earlier layer.
            shape(report, FAMILY / "report.schema.json")
            necessary_conditions(
                report, {original_report["report_id"]: original_report}
            )
            try:
                process_session_fit(
                    report,
                    bundle,
                    context,
                    profile,
                    profile_ref,
                )
            except ValueError as exc:
                require(
                    str(exc) == case["expected"],
                    f"{case['id']}: {exc}, expected {case['expected']}",
                )
            else:
                require(
                    case["expected"] == "accept",
                    "accepted process refusal: " + case["id"],
                )
        collision = json.loads(
            (FAMILY / "fixtures/two-producer-collision.json").read_text()
        )
        for report in collision["inputs"]:
            shape(report, FAMILY / "report.schema.json")
            necessary_conditions(report)
        try:
            check_import_collisions(collision["inputs"])
        except ValueError as exc:
            require(str(exc) == collision["expected"], "wrong-import-collision-refusal")
        else:
            raise ValueError("accepted two-producer import collision")
        check_import_collisions(
            [collision["inputs"][0], copy.deepcopy(collision["inputs"][0])]
        )

        # Boundary actor/threat arrays are sets, not an ordering-dependent claim.
        r = copy.deepcopy(examples["shared-account-process"])
        r["assessments"][0]["boundary"]["threats"].reverse()
        shape(r, FAMILY / "report.schema.json")
        necessary_conditions(r)

        # Unavailable optional hardware is valid data; no evidence is promoted.
        r = copy.deepcopy(baseline)
        for status in (
            "not-present",
            "inaccessible",
            "unsupported",
            "not-probed",
            "error",
            "unknown",
            "available",
        ):
            r["capabilities"][0]["status"] = status
            shape(r, FAMILY / "report.schema.json")
            necessary_conditions(r)
            require(
                r["assessments"][0]["value"] == "enrolled-key",
                "capability-promoted-binding",
            )
        r = copy.deepcopy(baseline)
        r["created_at"] = "2026-10-29T12:06:00Z"
        for a in r["assessments"]:
            a["state"] = "stale"
        shape(r, FAMILY / "report.schema.json")
        necessary_conditions(r)
    print(
        f"PASS: 4 dimension definitions, {len(examples)} examples, {len(schema_mutations)} shape rejects, {len(semantic_mutations)} semantic rejects, {len(process_cases)} process fit cases, 6 time shape refusals, 5 time binding/provenance refusals, two-producer collision, 7 capability states, stale history"
    )
    print(
        "Logical draft controls only; no native, cryptographic, policy or twin implementation qualification."
    )


if __name__ == "__main__":
    main()
