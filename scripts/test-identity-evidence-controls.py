#!/usr/bin/env python3
"""Draft shape, vocabulary parity and necessary-condition controls; no crypto."""

import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
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
    require(
        len({r["report_id"] for r in report["input_reports"]})
        == len(report["input_reports"]),
        "duplicate-reference",
    )
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
                if "key_ref" in c and (collection == "evidence" or "key_ref" in r):
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


def _extract_json_report(stdout, stderr):
    decoder = json.JSONDecoder()
    for stream in (stdout, stderr):
        if not stream:
            continue
        for match in re.finditer(r"(?:^|\n)\{", stream):
            start = match.end() - 1
            try:
                obj, _ = decoder.raw_decode(stream[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and ("files" in obj or "valid" in obj):
                return obj
    raise RuntimeError(
        f"goneat produced no structured JSON report (stdout={stdout[:200]!r}, stderr={stderr[:300]!r})"
    )


def verify_suite_report(report, expected_by_relpath, expected_count):
    summary = report.get("summary")
    files = report.get("files")
    if not isinstance(summary, dict) or not isinstance(files, list):
        raise RuntimeError(f"malformed goneat suite report: {report!r}")
    if summary.get("skipped", 0) != 0 or summary.get("unmapped", 0) != 0:
        raise RuntimeError(f"suite had skipped or unmapped files: {summary!r}")
    if (
        summary.get("total") != expected_count
        or summary.get("validated") != expected_count
    ):
        raise RuntimeError(
            f"suite count mismatch: expected {expected_count}, summary={summary!r}"
        )
    if len(files) != expected_count:
        raise RuntimeError(
            f"suite file list length mismatch: expected {expected_count}, got {len(files)}"
        )

    verdicts = {}
    seen_paths = set()
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise RuntimeError(f"malformed suite file entry: {entry!r}")
        rel_path = entry["path"].replace("\\", "/")
        if rel_path in seen_paths:
            raise RuntimeError(f"duplicate file path in suite report: {rel_path}")
        if rel_path not in expected_by_relpath:
            raise RuntimeError(f"unexpected file path in suite report: {rel_path}")
        seen_paths.add(rel_path)

        item_id, want_schema_id = expected_by_relpath[rel_path]
        schema_info = entry.get("schema")
        if not isinstance(schema_info, dict):
            raise RuntimeError(f"missing schema metadata for {rel_path}: {entry!r}")
        got_schema_id = str(schema_info.get("id", "")).replace("\\", "/")
        if schema_info.get("source") != "local" or got_schema_id != want_schema_id:
            raise RuntimeError(
                f"schema mapping mismatch for {rel_path}: got {schema_info!r}, expected local {want_schema_id!r}"
            )
        if entry.get("status") not in ("pass", "fail", "expected_fail"):
            raise RuntimeError(
                f"unexpected status for {rel_path}: {entry.get('status')!r}"
            )
        if "error" in entry and entry["error"]:
            raise RuntimeError(
                f"unable to validate {item_id} ({rel_path}): {entry['error']}"
            )
        valid = entry.get("valid")
        if not isinstance(valid, bool):
            raise RuntimeError(f"missing boolean verdict for {rel_path}: {entry!r}")
        if valid:
            if entry.get("errors"):
                raise RuntimeError(
                    f"inconsistent valid=true with errors for {rel_path}: {entry!r}"
                )
            verdicts[item_id] = True
        else:
            diagnostics = entry.get("errors")
            if not isinstance(diagnostics, list) or len(diagnostics) == 0:
                raise RuntimeError(
                    f"invalid verdict missing schema diagnostics for {item_id} ({rel_path}): {entry!r}"
                )
            verdicts[item_id] = False

    if seen_paths != set(expected_by_relpath):
        missing = sorted(set(expected_by_relpath) - seen_paths)
        raise RuntimeError(f"missing files from suite report: {missing}")

    return verdicts


def shape_suite(items, goneat_bin):
    """Batch-validate (item_id, schema_path, raw_json_text) via `goneat validate suite`."""
    if not items:
        return {}
    seen_ids = set()
    for item_id, _, _ in items:
        if item_id in seen_ids:
            raise RuntimeError(f"duplicate suite item id: {item_id}")
        seen_ids.add(item_id)

    with tempfile.TemporaryDirectory(prefix="identity-evidence-suite-") as tmp_str:
        tmp = Path(tmp_str)
        (tmp / ".git").mkdir()
        (tmp / "cases").mkdir()
        (tmp / "schemas").mkdir()

        schema_keys = {}
        expected_by_relpath = {}

        for idx, (item_id, schema_path, raw_json) in enumerate(items):
            src_schema = Path(schema_path).resolve()
            if not src_schema.is_file():
                raise RuntimeError(f"missing schema file: {src_schema}")
            try:
                schema_rel = src_schema.relative_to(ROOT.resolve()).as_posix()
            except ValueError as exc:
                raise RuntimeError(
                    f"schema outside repository root: {src_schema}"
                ) from exc
            if schema_rel not in schema_keys:
                key = schema_rel.replace("/", "__").removesuffix(".schema.json")
                schema_keys[schema_rel] = key
                dst_schema = tmp / "schemas" / schema_rel
                dst_schema.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src_schema, dst_schema)
                (tmp / "cases" / key).mkdir(parents=True, exist_ok=True)
            key = schema_keys[schema_rel]
            case_rel = f"cases/{key}/{idx:05d}.json"
            (tmp / case_rel).write_text(raw_json, encoding="utf-8")
            expected_by_relpath[case_rel] = (item_id, f"schemas/{schema_rel}")

        manifest_lines = ['version: "1.0.0"', "mappings:"]
        for schema_rel, key in sorted(schema_keys.items()):
            manifest_lines.extend(
                [
                    f'  - pattern: "cases/{key}/*.json"',
                    f'    schema_id: "schemas/{schema_rel}"',
                    "    source: local",
                ]
            )
        (tmp / "schema-mappings.yaml").write_text(
            "\n".join(manifest_lines) + "\n", encoding="utf-8"
        )

        try:
            proc = subprocess.run(
                [
                    goneat_bin,
                    "validate",
                    "suite",
                    "--data",
                    str(tmp / "cases"),
                    "--manifest",
                    "schema-mappings.yaml",
                    "--no-ignore",
                    "--fail-on-unmapped",
                    "--strict",
                    "--format",
                    "json",
                    "--log-level",
                    "error",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=120.0,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(
                f"goneat validate suite execution failed: {exc}"
            ) from exc

        if proc.returncode not in (0, 1):
            raise RuntimeError(
                f"goneat validate suite exited {proc.returncode}: {proc.stderr[:400]}"
            )

        report = _extract_json_report(proc.stdout, proc.stderr)
        return verify_suite_report(report, expected_by_relpath, len(items))


def suite_error_controls(goneat_bin):
    """Verify batched goneat suite rejects parse/range/schema errors as RuntimeError."""
    report_schema = FAMILY / "report.schema.json"
    for label, bad_item in (
        ("malformed_json", ("bad", report_schema, "{\n")),
        (
            "float64_overflow",
            ("huge", report_schema, '{"contract":"identity-evidence/v0","n":1e400}\n'),
        ),
        ("missing_schema", ("missing", FAMILY / "nonexistent.schema.json", "{}\n")),
    ):
        try:
            shape_suite([bad_item], goneat_bin)
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"suite_error_controls did not fail on {label}")


def main():
    goneat = shutil.which("goneat")
    require(goneat, "goneat is required")
    schema = json.loads((FAMILY / "report.schema.json").read_text(encoding="utf-8"))
    queued_shapes = []

    def shape(instance, schema_path, accepted=True):
        item_id = f"shape-{len(queued_shapes):05d}"
        queued_shapes.append(
            (item_id, Path(schema_path), json.dumps(instance), bool(accepted))
        )

    def flush_shapes():
        suite_items = [
            (item_id, schema_path, raw_json)
            for item_id, schema_path, raw_json, _ in queued_shapes
        ]
        verdicts = shape_suite(suite_items, goneat)
        for item_id, schema_path, _, accepted in queued_shapes:
            require(
                verdicts.get(item_id) is accepted,
                f"shape expectation failed for {item_id} ({schema_path.name}): got {verdicts.get(item_id)}, expected {accepted}",
            )

    # Verify fixture_digest rejects numeric and non-ASCII inputs outside its subset.
    for invalid_subset in ({"numeric": 1}, {"non_ascii": "é"}, {"key_é": True}):
        try:
            fixture_digest(invalid_subset)
        except ValueError as exc:
            require(str(exc) == "fixture-hash-subset", "wrong-fixture-subset-refusal")
        else:
            raise ValueError("accepted input outside fixture digest subset")

    # Wire admission vectors are shared data, not outputs captured from an adopter.
    time_example = json.loads(
        (FAMILY / "examples/time-attribution-mixed.json").read_text(encoding="utf-8")
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
    r["time_attribution"]["evidence"] = r["evidence"][0]["time_attribution"]["evidence"]
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
        necessary_conditions(carried, {attributed_input["report_id"]: attributed_input})
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
            ).read_text(encoding="utf-8")
        )
        shape(config, ROOT / "schemas/classifiers/v0/dimension-definition.schema.json")
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
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in (FAMILY / "examples").glob("*.json")
    }
    report_inputs = {r["report_id"]: r for r in examples.values()}
    for path in sorted((FAMILY / "examples").glob("*.json")):
        r = json.loads(path.read_text(encoding="utf-8"))
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
        require(str(exc) == "not-applicable-custody-has-key", "wrong-custody-refusal")
    else:
        raise ValueError("accepted not-applicable custody with a key")
    r = copy.deepcopy(examples["observation-only-installation"])
    del r["evidence"][0]["format_profile"]
    schema_mutations.append(r)
    r = copy.deepcopy(baseline)
    r["assessments"][0]["boundary"] = copy.deepcopy(
        examples["shared-account-process"]["assessments"][0]["boundary"]
    )
    schema_mutations.append(r)
    r = copy.deepcopy(baseline)
    r["assessments"][1]["claim_refs"] = ["claim-key-origin"]
    schema_mutations.append(r)
    r = copy.deepcopy(baseline)
    r["assessments"][1].update(value="unknown", state="current", evidence_refs=[])
    schema_mutations.append(r)
    r = copy.deepcopy(baseline)
    r["assessments"][1].update(value="software", state="unassessed")
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
    r = copy.deepcopy(examples["evaluated-installation"])
    dup_input = copy.deepcopy(r["input_reports"][0])
    dup_input["id"] = "source-observation-duplicate"
    r["input_reports"].append(dup_input)
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
    r = copy.deepcopy(examples["attested-key-origin-property"])
    other = copy.deepcopy(r["keys"][0])
    other["id"] = "key-other"
    r["keys"].append(other)
    r["assessments"][-1]["key_ref"] = "key-other"
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
            "property_profile": copy.deepcopy(source["identifiers"][0]["derivation"]),
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
    # Additional necessary-condition negative controls covering all remaining refusal branches.
    r = copy.deepcopy(baseline)
    r["capabilities"][0]["subject_ref"] = "unknown-subject-id"
    semantic_mutations.append((r, "unknown-subject"))
    r = copy.deepcopy(baseline)
    r["subjects"].append({"id": "subject-other", "kind": "session"})
    other_id = copy.deepcopy(r["identifiers"][0])
    other_id.update(id="identifier-other-subject", subject_ref="subject-other")
    r["identifiers"].append(other_id)
    r["evidence"][0]["identifier_ref"] = "identifier-other-subject"
    semantic_mutations.append((r, "identifier_ref-subject-mismatch"))
    r = copy.deepcopy(baseline)
    r["subjects"].append({"id": "subject-other", "kind": "session"})
    other_key = copy.deepcopy(r["keys"][0])
    other_key.update(id="key-other-subject", subject_ref="subject-other")
    r["keys"].append(other_key)
    r["evidence"][0]["key_ref"] = "key-other-subject"
    semantic_mutations.append((r, "key_ref-subject-mismatch"))
    r = copy.deepcopy(examples["attested-key-origin-property"])
    r["evidence"][0]["claim_refs"] = ["missing-claim"]
    semantic_mutations.append((r, "claim-subject-mismatch"))
    r = copy.deepcopy(examples["attested-key-origin-property"])
    r["subjects"].append({"id": "subject-other", "kind": "physical-device"})
    other_claim = copy.deepcopy(r["claims"][0])
    other_claim.update(id="claim-other-subject", subject_ref="subject-other")
    other_claim.pop("key_ref", None)
    r["claims"].append(other_claim)
    r["assessments"][-1]["claim_refs"] = ["claim-other-subject"]
    semantic_mutations.append((r, "claim-subject-mismatch"))
    r = copy.deepcopy(examples["shared-account-process"])
    r["assessments"][0]["boundary"]["comparison_subject_refs"] = ["subject-a"]
    semantic_mutations.append((r, "invalid-comparison-subject"))
    r = copy.deepcopy(examples["shared-account-process"])
    r["assessments"][0]["boundary"]["comparison_subject_refs"] = ["missing-neighbor"]
    semantic_mutations.append((r, "invalid-comparison-subject"))
    r = copy.deepcopy(baseline)
    r["evidence"][0]["collected_at"] = "2026-10-29T12:00:01Z"
    semantic_mutations.append((r, "future-evidence"))
    r = copy.deepcopy(baseline)
    r["capabilities"][0]["observed_at"] = "2026-10-29T12:00:01Z"
    semantic_mutations.append((r, "future-capability"))
    r = copy.deepcopy(examples["evaluated-installation"])
    r["input_reports"][0]["report_id"] = "unavailable-input-report"
    semantic_mutations.append((r, "input-report-unavailable"))
    r = copy.deepcopy(examples["evaluated-installation"])
    self_source = copy.deepcopy(examples["observation-only-installation"])
    self_source["report_id"] = "self-import-report"
    report_inputs["self-import-report"] = self_source
    r["report_id"] = "self-import-report"
    r["input_reports"][0].update(
        report_id="self-import-report", digest=fixture_digest(self_source)
    )
    semantic_mutations.append((r, "invalid-input-report"))
    r = copy.deepcopy(examples["evaluated-installation"])
    future_source = copy.deepcopy(examples["observation-only-installation"])
    future_source["report_id"] = "future-input-report"
    future_source["created_at"] = "2026-10-29T12:02:00Z"
    report_inputs["future-input-report"] = future_source
    r["input_reports"][0].update(
        report_id="future-input-report", digest=fixture_digest(future_source)
    )
    semantic_mutations.append((r, "invalid-input-report"))
    r = copy.deepcopy(examples["evaluated-installation"])
    r["evidence"][0]["origin"]["input_ref"] = "unknown-input-source"
    semantic_mutations.append((r, "unknown-input-report"))
    r = copy.deepcopy(baseline)
    r["assessments"][0]["assessed_at"] = "2026-10-29T12:00:01Z"
    semantic_mutations.append((r, "invalid-assessment-window"))
    r = copy.deepcopy(baseline)
    r["assessments"][0]["valid_until"] = r["assessments"][0]["assessed_at"]
    semantic_mutations.append((r, "invalid-assessment-window"))
    r = copy.deepcopy(baseline)
    r["created_at"] = "2026-10-29T12:01:00Z"
    r["evidence"][0]["collected_at"] = "2026-10-29T12:00:30Z"
    semantic_mutations.append((r, "evidence-after-assessment"))
    r = copy.deepcopy(examples["observed-installation"])
    r["assessments"][0]["value"] = "declared"
    semantic_mutations.append((r, "declaration-required"))
    r = copy.deepcopy(examples["observed-installation"])
    r["evidence"][0]["method"] = "declaration"
    semantic_mutations.append((r, "observation-required"))
    r = copy.deepcopy(baseline)
    r["assessments"][1]["evidence_refs"] = ["e-enroll"]
    semantic_mutations.append((r, "custody-observation-required"))
    r = copy.deepcopy(examples["shared-account-process"])
    r["assessments"][0]["value"] = "confidential-workload"
    semantic_mutations.append((r, "workload-attestation-required"))
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
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile_ref = {
        "id": profile["id"],
        "revision": "sha256:" + hashlib.sha256(profile_path.read_bytes()).hexdigest(),
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
    bundle = json.loads(
        (process_root / "evidence.example.json").read_text(encoding="utf-8")
    )
    shape(bundle, process_root / "evidence.schema.json")
    original_context = json.loads(
        (process_root / "evaluation-context.example.json").read_text(encoding="utf-8")
    )
    process_cases = json.loads(
        (process_root / "cases.json").read_text(encoding="utf-8")
    )
    process_cases += json.loads(
        (process_root / "report-cases.json").read_text(encoding="utf-8")
    )
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
        necessary_conditions(report, {original_report["report_id"]: original_report})
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

    def run_extra_process_fit(mutate_fn, expected):
        c_rep = copy.deepcopy(examples["local-process-session-launch"])
        c_bun = copy.deepcopy(bundle)
        c_ctx = copy.deepcopy(original_context)
        mutate_fn(c_rep, c_bun, c_ctx)
        shape(c_rep, FAMILY / "report.schema.json")
        shape(c_bun, process_root / "evidence.schema.json")
        necessary_conditions(c_rep)
        try:
            process_session_fit(c_rep, c_bun, c_ctx, profile, profile_ref)
        except ValueError as exc:
            require(
                str(exc) == expected,
                f"extra process fit got {exc}, expected {expected}",
            )
        else:
            require(
                expected == "accept",
                f"accepted extra process refusal: {expected}",
            )

    run_extra_process_fit(
        lambda _r, b, _c: b["profile"].update(
            id="urn:example:identity:other-profile:v0"
        ),
        "unsupported-evidence-profile",
    )
    run_extra_process_fit(
        lambda _r, b, _c: b["launch"].update(issued_at=b["launch"]["expires_at"]),
        "expired-or-invalid-window",
    )
    run_extra_process_fit(
        lambda _r, b, _c: b["launch"].update(expires_at="2026-10-29T12:05:01Z"),
        "expired-or-invalid-window",
    )
    run_extra_process_fit(
        lambda _r, b, _c: b["challenge"].update(issued_at="2026-10-29T12:00:09Z"),
        "expired-or-invalid-window",
    )
    run_extra_process_fit(
        lambda _r, _b, c: c.update(observed_at="2026-10-29T12:00:04Z"),
        "stale-process-observation",
    )
    run_extra_process_fit(
        lambda r, _b, _c: r["subjects"][0].update(kind="physical-device"),
        "process-session-subject-mismatch",
    )
    run_extra_process_fit(
        lambda r, _b, _c: r["keys"][0].update(public_key_digest="sha256:" + "a" * 64),
        "report-session-key-mismatch",
    )
    run_extra_process_fit(
        lambda _r, b, _c: b["launch"].update(process_digest="sha256:" + "b" * 64),
        "receipt-binding-mismatch",
    )

    def _mutate_challenge_receipt(_r, b, c):
        b["challenge"]["receipt_digest"] = "sha256:" + "c" * 64
        c["verified_receipt_digest"] = fixture_digest(b["launch"])

    run_extra_process_fit(_mutate_challenge_receipt, "challenge-receipt-mismatch")
    run_extra_process_fit(
        lambda r, _b, _c: r["claims"][0].update(property="other-property"),
        "process-session-claim-mismatch",
    )

    def _mutate_assessment_process_binding(r, _b, _c):
        r["assessments"][2]["rule"]["id"] = "urn:example:identity:other-rule:v0"

    run_extra_process_fit(
        _mutate_assessment_process_binding, "assessment-process-binding-mismatch"
    )
    run_extra_process_fit(
        lambda r, _b, _c: r["assessments"].pop(0),
        "process-session-assessments-required",
    )
    run_extra_process_fit(
        lambda _r, _b, c: c.update(
            now="2026-10-29T11:59:59Z", observed_at="2026-10-29T11:59:59Z"
        ),
        "assessment-not-current",
    )

    collision = json.loads(
        (FAMILY / "fixtures/two-producer-collision.json").read_text(encoding="utf-8")
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

    flush_shapes()
    suite_error_controls(goneat)
    print(
        f"PASS: 4 dimension definitions, {len(examples)} examples, {len(schema_mutations)} shape rejects, {len(semantic_mutations)} semantic rejects, {len(process_cases)} process fit cases (+13 boundary/refusal controls), 6 time shape refusals, 5 time binding/provenance refusals, two-producer collision, 7 capability states, stale history, batched suite error controls"
    )
    print(
        "Logical draft controls only; no native, cryptographic, policy or twin implementation qualification."
    )


if __name__ == "__main__":
    main()
