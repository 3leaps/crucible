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


NATIVE_CONTEXT_FACTS = (
    "security_principal",
    "namespace_context_digest",
    "executable_digest",
    "arguments_digest",
    "security_context_digest",
)
VALID_CLONE_BEHAVIORS = ("unknown", "copyable", "regenerated", "device-bound")
UTC_INSTANT_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


def _u32_be(n):
    return int(n).to_bytes(4, "big", signed=False)


def derive_arguments_digest(argv_bytes_list):
    pre = b"3leaps.native-process-observation.arguments.v0\x00" + _u32_be(
        len(argv_bytes_list)
    )
    for arg in argv_bytes_list:
        pre += _u32_be(len(arg)) + arg
    return "sha256:" + hashlib.sha256(pre).hexdigest()


def derive_executable_digest(image_bytes):
    pre = b"3leaps.native-process-observation.executable-image.v0\x00" + image_bytes
    return "sha256:" + hashlib.sha256(pre).hexdigest()


def derive_linux_namespace_context_digest(ns_map, obs_profile):
    drv = obs_profile["context_derivations"]["namespace_context_digest"][
        "urn:3leaps:identity-evidence:context-derivation:linux-ns-inum-set:v0"
    ]
    kinds = drv["namespace_kinds"]
    require(set(ns_map.keys()) == set(kinds), "incomplete-linux-namespace-set")
    pre = b"3leaps.native-process-observation.namespaces.v0\x00" + _u32_be(len(kinds))
    for kind in kinds:
        val = ns_map[kind]
        require(re.fullmatch(drv["entry_pattern"], val), "invalid-linux-ns-entry")
        kb, vb = kind.encode("ascii"), val.encode("ascii")
        pre += _u32_be(len(kb)) + kb + _u32_be(len(vb)) + vb
    return "sha256:" + hashlib.sha256(pre).hexdigest()


def derive_linux_security_context_digest(canonical_context_bytes):
    scheme = (
        b"urn:3leaps:identity-evidence:context-derivation:linux-procfs-status-secctx:v0"
    )
    pre = (
        b"3leaps.native-process-observation.security-context.v0\x00"
        + _u32_be(len(scheme))
        + scheme
        + b"\x00"
        + _u32_be(len(canonical_context_bytes))
        + canonical_context_bytes
    )
    return "sha256:" + hashlib.sha256(pre).hexdigest()


def project_host_scope_urn(host_scope, obs_profile):
    spec = obs_profile["host_scope_projection"]
    parts = (
        host_scope["namespace"],
        host_scope["value"],
        host_scope["derivation"]["id"],
        host_scope["derivation"]["revision"],
        host_scope["stability"],
        host_scope["clone_behavior"],
    )
    pre = spec["domain"].encode("ascii") + b"\x00"
    for p in parts:
        pb = p.encode("utf-8")
        pre += _u32_be(len(pb)) + pb
    return spec["urn_prefix"] + hashlib.sha256(pre).hexdigest()


def _parse_strict_utc(value):
    if type(value) is not str or not UTC_INSTANT_RE.fullmatch(value):
        return None
    try:
        return instant(value)
    except ValueError:
        return None


def admit_live_observation(
    obs, now_utc, obs_profile, obs_profile_ref, report=None, input_reports=None
):
    """Standalone freshness and report-time binding gate for live observation consumers."""
    now_dt = _parse_strict_utc(now_utc)
    require(now_dt is not None, "trusted-clock-unavailable")
    require(obs.get("profile") == obs_profile_ref, "unsupported-evidence-profile")
    obs_dt = _parse_strict_utc(obs.get("observed_at"))
    require(obs_dt is not None, "invalid-observed-at")
    if report is not None:
        necessary_conditions(report, input_reports)
        obs_digest = fixture_digest(obs)
        matched = [
            e
            for e in report["evidence"]
            if e["format_profile"] == obs_profile_ref or e["digest"] == obs_digest
        ]
        require(len(matched) == 1, "observation-evidence-descriptor-missing")
        ev = matched[0]
        require(
            ev["format_profile"] == obs_profile_ref
            and ev["digest"] == obs_digest
            and ev["method"] == "os-observation"
            and ev["subject_ref"] == obs["process"]["subject_ref"]
            and ev["collected_at"] == obs["observed_at"],
            "observation-evidence-descriptor-mismatch",
        )
    age = (now_dt - obs_dt).total_seconds()
    require(
        age >= -obs_profile["max_future_skew_seconds"],
        "future-process-observation",
    )
    require(
        age <= obs_profile["max_observation_age_seconds"],
        "stale-process-observation",
    )


def _validate_start_subprofile(obs, obs_profile):
    start = obs["process"]["start_identity"]
    sub_id = start["profile"]["id"]
    sub = obs_profile["start_identity_profiles"].get(sub_id)
    if (
        sub is None
        or sub["status"] == "reserved"
        or start["profile"]["revision"] != sub["revision"]
    ):
        return None, "insufficient:unsupported-start-identity-profile"
    if obs["observer"]["platform_family"] != sub["platform_family"]:
        return None, "insufficient:inconsistent-observation"
    return sub, None


def _validate_linux_ns_id(value, pattern, sub):
    if not re.fullmatch(pattern, value):
        return False
    _, maj_s, min_s, ino_s = value.split(":")
    return (
        int(maj_s) <= int(sub["dev_major_max_u32"])
        and int(min_s) <= int(sub["dev_minor_max_u32"])
        and int(ino_s) <= int(sub["value_max_u64"])
    )


def _validate_start_value(value, sub):
    if not re.fullmatch(sub["value_pattern"], value):
        return False
    if "value_max_u64" in sub:
        return int(value) <= int(sub["value_max_u64"])
    sec_s, _ = value.split(".")
    return int(sec_s) <= int(sub["seconds_max_i64"])


def _validate_context_derivation(fact_name, fact_obj, platform_family, obs_profile):
    drv_ref = fact_obj.get("derivation")
    if not isinstance(drv_ref, dict):
        return False
    drv = (
        obs_profile["context_derivations"].get(fact_name, {}).get(drv_ref.get("id", ""))
    )
    if (
        drv is None
        or drv["status"] != "draft"
        or drv["revision"] != drv_ref.get("revision")
        or platform_family not in drv["platforms"]
    ):
        return False
    if fact_name == "security_principal":
        p = fact_obj.get("principal", {})
        if p.get("namespace") != drv["principal_namespace"] or not re.fullmatch(
            drv["value_pattern"], p.get("value", "")
        ):
            return False
    return True


def _context_fact_payload(fact_name, fact_obj):
    return (
        fact_obj["principal"]
        if fact_name == "security_principal"
        else fact_obj["digest"]
    )


def _validate_comparison_policy(policy):
    if not isinstance(policy, dict):
        return False, None, None
    required_keys = {
        "baseline_host_scope_trusted",
        "candidate_host_scope_trusted",
        "require_live",
        "required_context_facts",
        "detect_observed_context_drift",
    }
    optional_keys = {"allowed_clone_behaviors"}
    if not required_keys.issubset(policy.keys()) or not set(policy.keys()).issubset(
        required_keys | optional_keys
    ):
        return False, None, None
    for bkey in (
        "baseline_host_scope_trusted",
        "candidate_host_scope_trusted",
        "require_live",
        "detect_observed_context_drift",
    ):
        if type(policy[bkey]) is not bool:
            return False, None, None
    req_facts = policy["required_context_facts"]
    if not isinstance(req_facts, (list, tuple)) or any(
        type(f) is not str or f not in NATIVE_CONTEXT_FACTS for f in req_facts
    ):
        return False, None, None
    allowed_clones = None
    if "allowed_clone_behaviors" in policy:
        ac = policy["allowed_clone_behaviors"]
        if (
            not isinstance(ac, (list, tuple))
            or len(ac) == 0
            or any(type(c) is not str or c not in VALID_CLONE_BEHAVIORS for c in ac)
        ):
            return False, None, None
        allowed_clones = set(ac)
    return True, set(req_facts), allowed_clones


def compare_native_observations(
    baseline, candidate, policy, obs_profile, obs_profile_ref
):
    """Deterministic native-process-observation comparison control; no OS syscalls."""
    pol_ok, req_facts_set, allowed_clones = _validate_comparison_policy(policy)
    if not pol_ok:
        return "insufficient:invalid-evaluation-policy"
    if (
        baseline.get("profile") != obs_profile_ref
        or candidate.get("profile") != obs_profile_ref
    ):
        return "insufficient:unsupported-evidence-profile"
    if not (
        baseline["observer"]["bracketed"] is True
        and candidate["observer"]["bracketed"] is True
    ):
        return "insufficient:unbracketed-observation"
    base_sub, err = _validate_start_subprofile(baseline, obs_profile)
    if err is not None:
        return err
    cand_sub, err = _validate_start_subprofile(candidate, obs_profile)
    if err is not None:
        return err

    b_proc, c_proc = baseline["process"], candidate["process"]
    established = set(obs_profile["established_host_scope_stabilities"])
    if (
        policy["baseline_host_scope_trusted"] is not True
        or policy["candidate_host_scope_trusted"] is not True
        or b_proc["host_scope"]["stability"] not in established
        or c_proc["host_scope"]["stability"] not in established
    ):
        return "insufficient:unestablished-host-scope"
    for key in ("namespace", "value", "derivation"):
        if b_proc["host_scope"][key] != c_proc["host_scope"][key]:
            return "mismatch:host-scope-mismatch"
    if (
        b_proc["host_scope"]["stability"] != c_proc["host_scope"]["stability"]
        or b_proc["host_scope"]["clone_behavior"]
        != c_proc["host_scope"]["clone_behavior"]
    ):
        return "insufficient:inconsistent-host-scope-metadata"
    if allowed_clones is not None and (
        b_proc["host_scope"]["clone_behavior"] not in allowed_clones
        or c_proc["host_scope"]["clone_behavior"] not in allowed_clones
    ):
        return "insufficient:disallowed-clone-behavior"

    if (
        b_proc["boot_id"]["status"] != "observed"
        or c_proc["boot_id"]["status"] != "observed"
    ):
        return "insufficient:missing-boot-id"
    if not re.fullmatch(
        base_sub["boot_id_pattern"], b_proc["boot_id"]["value"]
    ) or not re.fullmatch(cand_sub["boot_id_pattern"], c_proc["boot_id"]["value"]):
        return "insufficient:invalid-boot-id"
    if b_proc["boot_id"]["value"] != c_proc["boot_id"]["value"]:
        return "mismatch:boot-id-mismatch"

    if b_proc["start_identity"]["profile"] != c_proc["start_identity"]["profile"]:
        return "insufficient:incompatible-start-identity-profile"

    ns_policy = base_sub["pid_namespace_policy"]
    if ns_policy == "required-observed":
        if (
            b_proc["pid_numbering_namespace"]["status"] != "observed"
            or c_proc["pid_numbering_namespace"]["status"] != "observed"
        ):
            return "insufficient:missing-pid-numbering-namespace"
        for ns_val in (
            b_proc["pid_numbering_namespace"]["value"],
            c_proc["pid_numbering_namespace"]["value"],
        ):
            if not _validate_linux_ns_id(
                ns_val, base_sub["pid_namespace_pattern"], base_sub
            ):
                return "insufficient:invalid-pid-namespace"
        if (
            b_proc["pid_numbering_namespace"]["value"]
            != c_proc["pid_numbering_namespace"]["value"]
        ):
            return "insufficient:pid-numbering-namespace-mismatch"
        b_tns = baseline["observer"]["time_namespace"]
        c_tns = candidate["observer"]["time_namespace"]
        for tns in (b_tns, c_tns):
            if tns["status"] not in {"observed", "not-present"}:
                return "insufficient:missing-observer-time-namespace"
            if tns["status"] == "observed" and not _validate_linux_ns_id(
                tns["value"], base_sub["observer_time_namespace_pattern"], base_sub
            ):
                return "insufficient:invalid-observer-time-namespace"
        if b_tns["status"] != c_tns["status"] or (
            b_tns["status"] == "observed" and b_tns["value"] != c_tns["value"]
        ):
            return "insufficient:observer-time-namespace-mismatch"
    elif ns_policy == "unsupported-not-applicable":
        for item in (baseline, candidate):
            proc = item["process"]
            if (
                proc["pid_numbering_namespace"]["status"] != "unsupported"
                or proc["target_pid_namespace"]["status"] != "unsupported"
                or item["observer"]["time_namespace"]["status"] != "unsupported"
            ):
                return "insufficient:inconsistent-observation"
    else:
        return "insufficient:inconsistent-observation"

    min_pid = int(obs_profile["pid_range"]["min"])
    max_pid = int(obs_profile["pid_range"]["max"])
    if not (
        re.fullmatch(r"[1-9][0-9]{0,9}", b_proc["pid"])
        and re.fullmatch(r"[1-9][0-9]{0,9}", c_proc["pid"])
        and min_pid <= int(b_proc["pid"]) <= max_pid
        and min_pid <= int(c_proc["pid"]) <= max_pid
    ):
        return "insufficient:invalid-pid-range"
    if b_proc["pid"] != c_proc["pid"]:
        return "mismatch:pid-mismatch"

    if (
        b_proc["process_state"]["status"] == "observed"
        and b_proc["start_identity"]["status"] == "observed"
        and (
            c_proc["process_state"]["status"] == "not-present"
            or c_proc["start_identity"]["status"] == "not-present"
        )
    ):
        return "mismatch:process-exited"

    if ns_policy == "required-observed":
        if (
            b_proc["target_pid_namespace"]["status"] != "observed"
            or c_proc["target_pid_namespace"]["status"] != "observed"
        ):
            return "insufficient:missing-target-pid-namespace"
        for ns_val in (
            b_proc["target_pid_namespace"]["value"],
            c_proc["target_pid_namespace"]["value"],
        ):
            if not _validate_linux_ns_id(
                ns_val, base_sub["pid_namespace_pattern"], base_sub
            ):
                return "insufficient:invalid-pid-namespace"
        if (
            b_proc["target_pid_namespace"]["value"]
            != c_proc["target_pid_namespace"]["value"]
        ):
            return "mismatch:target-pid-namespace-mismatch"

    if (
        b_proc["start_identity"]["status"] != "observed"
        or c_proc["start_identity"]["status"] != "observed"
    ):
        return "insufficient:missing-start-identity"
    if not _validate_start_value(
        b_proc["start_identity"]["value"], base_sub
    ) or not _validate_start_value(c_proc["start_identity"]["value"], base_sub):
        return "insufficient:invalid-start-identity"
    if b_proc["start_identity"]["value"] != c_proc["start_identity"]["value"]:
        return "mismatch:start-identity-mismatch"

    if (
        b_proc["process_state"]["status"] != "observed"
        or c_proc["process_state"]["status"] != "observed"
    ):
        return "insufficient:missing-process-state"
    if policy["require_live"] and c_proc["process_state"]["value"] != "live":
        return "mismatch:process-not-live"

    b_ctx, c_ctx = b_proc["execution_context"], c_proc["execution_context"]
    plat = baseline["observer"]["platform_family"]
    canonical_order = tuple(obs_profile["canonical_context_fact_order"])
    # Step 8a: verify accepted derivations on all observed context facts.
    for fact in canonical_order:
        for side_ctx in (b_ctx, c_ctx):
            if side_ctx[fact][
                "status"
            ] == "observed" and not _validate_context_derivation(
                fact, side_ctx[fact], plat, obs_profile
            ):
                return f"insufficient:unsupported-context-derivation-{fact}"
    # Step 8b (Pass 1): missing required facts in canonical schema order.
    for fact in canonical_order:
        if fact in req_facts_set and (
            b_ctx[fact]["status"] != "observed" or c_ctx[fact]["status"] != "observed"
        ):
            return f"insufficient:missing-context-{fact}"
    # Step 8c (Pass 2): derivation compatibility in canonical schema order.
    for fact in canonical_order:
        both_obs = (
            b_ctx[fact]["status"] == "observed" and c_ctx[fact]["status"] == "observed"
        )
        if both_obs and (
            fact in req_facts_set or policy["detect_observed_context_drift"]
        ):
            if b_ctx[fact]["derivation"] != c_ctx[fact]["derivation"]:
                return f"insufficient:incompatible-context-derivation-{fact}"
    # Step 8d (Pass 3): value/digest equality in canonical schema order.
    for fact in canonical_order:
        both_obs = (
            b_ctx[fact]["status"] == "observed" and c_ctx[fact]["status"] == "observed"
        )
        if both_obs and (
            fact in req_facts_set or policy["detect_observed_context_drift"]
        ):
            if _context_fact_payload(fact, b_ctx[fact]) != _context_fact_payload(
                fact, c_ctx[fact]
            ):
                return f"mismatch:context-changed-{fact}"

    return "match"


def project_to_local_process_session_process(
    obs,
    host_scope_trusted,
    now_utc,
    obs_profile,
    obs_profile_ref,
    report=None,
    input_reports=None,
    allowed_clone_behaviors=None,
):
    """Fail-closed adapter from native-process-observation to local-process-session process."""
    require(type(host_scope_trusted) is bool, "invalid-evaluation-policy")
    admit_live_observation(
        obs,
        now_utc,
        obs_profile,
        obs_profile_ref,
        report=report,
        input_reports=input_reports,
    )
    require(obs["observer"]["bracketed"] is True, "unbracketed-observation")
    sub, err = _validate_start_subprofile(obs, obs_profile)
    require(err is None, err or "invalid-subprofile")
    proc = obs["process"]
    require(
        host_scope_trusted is True
        and proc["host_scope"]["stability"]
        in set(obs_profile["established_host_scope_stabilities"]),
        "unestablished-host-scope",
    )
    if allowed_clone_behaviors is not None:
        require(
            proc["host_scope"]["clone_behavior"] in set(allowed_clone_behaviors),
            "disallowed-clone-behavior",
        )
    require(
        proc["process_state"]["status"] == "observed"
        and proc["process_state"]["value"] == "live",
        "process-not-live",
    )
    require(
        proc["boot_id"]["status"] == "observed"
        and bool(re.fullmatch(sub["boot_id_pattern"], proc["boot_id"]["value"])),
        "missing-or-invalid-boot-id",
    )
    require(
        proc["start_identity"]["status"] == "observed"
        and _validate_start_value(proc["start_identity"]["value"], sub),
        "missing-or-invalid-start-identity",
    )
    require(
        proc["pid_numbering_namespace"]["status"] == "observed"
        and proc["target_pid_namespace"]["status"] == "observed",
        "missing-pid-namespace-for-session-bundle",
    )
    require(
        _validate_linux_ns_id(
            proc["pid_numbering_namespace"]["value"], sub["pid_namespace_pattern"], sub
        )
        and _validate_linux_ns_id(
            proc["target_pid_namespace"]["value"], sub["pid_namespace_pattern"], sub
        )
        and proc["pid_numbering_namespace"]["value"]
        == proc["target_pid_namespace"]["value"],
        "ambiguous-pid-namespace-for-session-bundle",
    )
    tns = obs["observer"]["time_namespace"]
    require(
        tns["status"] in {"observed", "not-present"}
        and (
            tns["status"] == "not-present"
            or _validate_linux_ns_id(
                tns["value"], sub["observer_time_namespace_pattern"], sub
            )
        ),
        "invalid-observer-time-namespace-for-session-bundle",
    )
    ctx = proc["execution_context"]
    plat = obs["observer"]["platform_family"]
    for fact in NATIVE_CONTEXT_FACTS:
        require(
            ctx[fact]["status"] == "observed",
            f"missing-context-for-session-bundle:{fact}",
        )
        require(
            _validate_context_derivation(fact, ctx[fact], plat, obs_profile),
            f"unsupported-context-derivation:{fact}",
        )
    projected_host_scope = project_host_scope_urn(proc["host_scope"], obs_profile)
    require(len(projected_host_scope) <= 512, "projected-host-scope-too-long")
    return {
        "subject_ref": proc["subject_ref"],
        "host_scope": projected_host_scope,
        "boot_id": proc["boot_id"]["value"],
        "pid_namespace": proc["target_pid_namespace"]["value"],
        "pid": proc["pid"],
        "start_identity": {
            "profile": copy.deepcopy(proc["start_identity"]["profile"]),
            "value": proc["start_identity"]["value"],
        },
        "execution_context": {
            "security_principal": copy.deepcopy(ctx["security_principal"]["principal"]),
            "namespace_context_digest": ctx["namespace_context_digest"]["digest"],
            "executable_digest": ctx["executable_digest"]["digest"],
            "arguments_digest": ctx["arguments_digest"]["digest"],
            "security_context_digest": ctx["security_context_digest"]["digest"],
        },
    }


def bind_native_observation_report(report, obs, obs_profile_ref):
    """Verify observation-only report descriptor binding to a native-process-observation payload."""
    require(obs.get("profile") == obs_profile_ref, "unsupported-evidence-profile")
    require(
        report["assessments"] == [] and "evaluator" not in report,
        "observation-report-not-observation-only",
    )
    subjects = {s["id"]: s for s in report["subjects"]}
    proc = obs["process"]
    require(
        subjects.get(proc["subject_ref"], {}).get("kind") == "process",
        "observation-subject-not-process",
    )
    if "identifier_ref" in proc["host_scope"]:
        ident = next(
            (
                x
                for x in report["identifiers"]
                if x["id"] == proc["host_scope"]["identifier_ref"]
            ),
            None,
        )
        require(
            ident is not None
            and subjects.get(ident["subject_ref"], {}).get("kind")
            in {"os-installation", "physical-device", "virtual-machine", "container"}
            and all(
                ident[k] == proc["host_scope"][k]
                for k in (
                    "namespace",
                    "value",
                    "derivation",
                    "stability",
                    "clone_behavior",
                )
            ),
            "host-scope-identifier-mismatch",
        )
    obs_digest = fixture_digest(obs)
    matched = [
        e
        for e in report["evidence"]
        if e["format_profile"] == obs_profile_ref or e["digest"] == obs_digest
    ]
    require(len(matched) == 1, "observation-evidence-descriptor-missing")
    ev = matched[0]
    require(
        ev["format_profile"] == obs_profile_ref
        and ev["digest"] == obs_digest
        and ev["method"] == "os-observation"
        and ev["subject_ref"] == proc["subject_ref"]
        and ev["collected_at"] == obs["observed_at"]
        and "key_ref" not in ev
        and "identifier_ref" not in ev
        and "boundary" not in ev,
        "observation-evidence-descriptor-mismatch",
    )


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

    # Native process observation profile pins, 7-state bijection, shape, comparison & projection controls.
    obs_root = FAMILY / "profiles/native-process-observation"
    obs_profile_path = obs_root / "profile.json"
    obs_schema_path = obs_root / "evidence.schema.json"
    obs_readme_path = obs_root / "README.md"
    obs_profile = json.loads(obs_profile_path.read_text(encoding="utf-8"))
    obs_schema = json.loads(obs_schema_path.read_text(encoding="utf-8"))
    obs_readme_digest = (
        "sha256:" + hashlib.sha256(obs_readme_path.read_bytes()).hexdigest()
    )
    obs_schema_digest = (
        "sha256:" + hashlib.sha256(obs_schema_path.read_bytes()).hexdigest()
    )
    obs_profile_ref = {
        "id": obs_profile["id"],
        "revision": "sha256:"
        + hashlib.sha256(obs_profile_path.read_bytes()).hexdigest(),
    }
    require(
        obs_profile["specification"]["revision"] == obs_readme_digest,
        "native-obs-specification-pin-drift",
    )
    require(
        obs_profile["evidence_schema"]["revision"] == obs_schema_digest,
        "native-obs-schema-pin-drift",
    )
    for sub in obs_profile["start_identity_profiles"].values():
        require(
            sub["revision"] == obs_readme_digest,
            "native-obs-subprofile-pin-drift",
        )
    for fact_map in obs_profile["context_derivations"].values():
        for drv in fact_map.values():
            require(
                drv["revision"] == obs_readme_digest,
                "native-obs-context-derivation-pin-drift",
            )
    fact_statuses = obs_schema["$defs"]["fact-status"]["enum"]
    cap_statuses = schema["$defs"]["capability"]["properties"]["status"]["enum"]
    mapping = obs_profile["status_mapping"]
    require(
        list(mapping.keys()) == fact_statuses
        and set(mapping.values()) == set(cap_statuses)
        and len(set(mapping.values())) == len(fact_statuses) == 7
        and mapping["observed"] == "available",
        "native-obs-status-bijection-drift",
    )

    macos_obs = json.loads(
        (obs_root / "evidence.example.json").read_text(encoding="utf-8")
    )
    linux_obs = json.loads(
        (obs_root / "evidence.linux.example.json").read_text(encoding="utf-8")
    )
    shape(macos_obs, obs_schema_path)
    shape(linux_obs, obs_schema_path)
    bind_native_observation_report(
        examples["native-process-observation"], macos_obs, obs_profile_ref
    )

    # Golden preimage recomputation assertions (entarch E4 + devrev M4 / DR-NPO-R1-5).
    golden_argv_digest = derive_arguments_digest([b"/usr/bin/sleep", b"300"])
    golden_exe_digest = derive_executable_digest(b"\x7fELF-synthetic-sleep-image-v0\n")
    golden_ns_map = {
        "cgroup": "ns:0:4:4026531835",
        "ipc": "ns:0:4:4026531839",
        "mnt": "ns:0:4:4026531840",
        "net": "ns:0:4:4026531992",
        "pid": "ns:0:4:4026531836",
        "time": "ns:0:4:4026531834",
        "time_for_children": "ns:0:4:4026531834",
        "user": "ns:0:4:4026531837",
        "uts": "ns:0:4:4026531838",
    }
    golden_ns_digest = derive_linux_namespace_context_digest(golden_ns_map, obs_profile)
    golden_sec_digest = derive_linux_security_context_digest(
        b"groups=27,1000;no_new_privs=1;seccomp=2;cap_inh=0000000000000000;cap_prm=0000000000000000;cap_eff=0000000000000000;cap_bnd=000001ffffffffff;cap_amb=0000000000000000"
    )
    require(
        linux_obs["process"]["execution_context"]["arguments_digest"]["digest"]
        == golden_argv_digest
        and linux_obs["process"]["execution_context"]["executable_digest"]["digest"]
        == golden_exe_digest
        and linux_obs["process"]["execution_context"]["namespace_context_digest"][
            "digest"
        ]
        == golden_ns_digest
        and linux_obs["process"]["execution_context"]["security_context_digest"][
            "digest"
        ]
        == golden_sec_digest,
        "golden-context-preimage-drift",
    )
    # Reversed dict insertion order produces identical namespace digest; missing kind refuses.
    require(
        derive_linux_namespace_context_digest(
            dict(reversed(list(golden_ns_map.items()))), obs_profile
        )
        == golden_ns_digest,
        "namespace-digest-order-drift",
    )
    try:
        derive_linux_namespace_context_digest(
            {k: v for k, v in golden_ns_map.items() if k != "time"}, obs_profile
        )
    except ValueError as exc:
        require(
            str(exc) == "incomplete-linux-namespace-set",
            f"unexpected partial ns refusal: {exc}",
        )
    else:
        raise ValueError("accepted partial linux namespace set")
    require(
        project_host_scope_urn(linux_obs["process"]["host_scope"], obs_profile)
        == "urn:3leaps:identity-evidence:host-scope:v0:sha256:8e3d1953b6494fc7c0399bf1487b90e57917b9a0651670dd83bc62a0af5d0a8d",
        "golden-host-scope-projection-drift",
    )

    # Binder payload-profile substitution negative controls (DR-NPO-R1-4).
    for mut_field, mut_val in (
        ("id", "urn:example:identity:other-obs-profile:v0"),
        ("revision", "sha256:" + "0" * 64),
    ):
        bad_payload = copy.deepcopy(macos_obs)
        bad_payload["profile"][mut_field] = mut_val
        bad_rep = copy.deepcopy(examples["native-process-observation"])
        bad_rep["evidence"][0]["digest"] = fixture_digest(bad_payload)
        shape(bad_payload, obs_schema_path)
        shape(bad_rep, FAMILY / "report.schema.json")
        try:
            bind_native_observation_report(bad_rep, bad_payload, obs_profile_ref)
        except ValueError as exc:
            require(
                str(exc) == "unsupported-evidence-profile",
                f"wrong binder profile refusal: {exc}",
            )
        else:
            raise ValueError("accepted substituted payload profile in binder")

    # Standalone freshness and imported collected_at binding controls (entarch E3 + devrev L2).
    admit_live_observation(
        macos_obs,
        "2026-10-29T12:00:00Z",
        obs_profile,
        obs_profile_ref,
        report=examples["native-process-observation"],
    )
    admit_live_observation(
        macos_obs,
        "2026-10-29T12:00:05Z",
        obs_profile,
        obs_profile_ref,
        report=examples["native-process-observation"],
    )
    freshness_refusals = [
        (macos_obs, None, None, None, "trusted-clock-unavailable"),
        (macos_obs, "not-a-utc-timestamp", None, None, "trusted-clock-unavailable"),
        (
            macos_obs,
            "2026-10-29T11:59:59Z",
            examples["native-process-observation"],
            None,
            "future-process-observation",
        ),
        (
            macos_obs,
            "2026-10-29T12:00:06Z",
            examples["native-process-observation"],
            None,
            "stale-process-observation",
        ),
    ]
    obs_year_2000 = copy.deepcopy(macos_obs)
    obs_year_2000["observed_at"] = "2000-01-01T00:00:00Z"
    freshness_refusals.append(
        (
            obs_year_2000,
            "2026-10-29T12:00:00Z",
            None,
            None,
            "stale-process-observation",
        )
    )
    obs_year_2099 = copy.deepcopy(macos_obs)
    obs_year_2099["observed_at"] = "2099-01-01T00:00:00Z"
    freshness_refusals.append(
        (
            obs_year_2099,
            "2026-10-29T12:00:00Z",
            None,
            None,
            "future-process-observation",
        )
    )
    # Imported stale report wrapped in a fresh evaluation report at 12:00:10Z:
    # carried-forward evidence retains collected_at=12:00:00Z, refusing as stale at 12:00:10Z.
    fresh_wrapper = copy.deepcopy(examples["native-process-observation"])
    fresh_wrapper["report_id"] = "wrapper-importing-stale-obs"
    fresh_wrapper["created_at"] = "2026-10-29T12:00:10Z"
    fresh_wrapper["input_reports"] = [
        {
            "id": "src-obs",
            "report_id": examples["native-process-observation"]["report_id"],
            "digest": fixture_digest(examples["native-process-observation"]),
        }
    ]
    fresh_wrapper["evidence"][0]["origin"] = {
        "input_ref": "src-obs",
        "record_ref": fresh_wrapper["evidence"][0]["id"],
    }
    freshness_refusals.append(
        (
            macos_obs,
            "2026-10-29T12:00:10Z",
            fresh_wrapper,
            {
                examples["native-process-observation"]["report_id"]: examples[
                    "native-process-observation"
                ]
            },
            "stale-process-observation",
        )
    )
    for f_obs, f_now, f_rep, f_inputs, expected_err in freshness_refusals:
        shape(f_obs, obs_schema_path)
        if f_rep is not None:
            shape(f_rep, FAMILY / "report.schema.json")
        try:
            admit_live_observation(
                f_obs,
                f_now,
                obs_profile,
                obs_profile_ref,
                report=f_rep,
                input_reports=f_inputs,
            )
        except ValueError as exc:
            require(
                str(exc) == expected_err,
                f"freshness refusal got {exc}, expected {expected_err}",
            )
        else:
            raise ValueError(f"accepted invalid freshness case: {expected_err}")

    # All 7 fact states are representable on context facts when conditional rules hold.
    argv_drv_ref = copy.deepcopy(
        linux_obs["process"]["execution_context"]["arguments_digest"]["derivation"]
    )
    for fact_state in fact_statuses:
        m = copy.deepcopy(macos_obs)
        if fact_state == "observed":
            m["process"]["execution_context"]["arguments_digest"] = {
                "status": "observed",
                "derivation": copy.deepcopy(argv_drv_ref),
                "digest": golden_argv_digest,
            }
        else:
            m["process"]["execution_context"]["arguments_digest"] = {
                "status": fact_state,
                "reason": f"synthetic-{fact_state}",
            }
        shape(m, obs_schema_path)

    obs_shape_rejects = []
    # Conditional presence/absence violations across fact wrappers (including derivation).
    m = copy.deepcopy(macos_obs)
    del m["process"]["boot_id"]["value"]
    obs_shape_rejects.append(m)
    m = copy.deepcopy(macos_obs)
    m["process"]["pid_numbering_namespace"]["value"] = "pidns:0:4:1"
    obs_shape_rejects.append(m)
    m = copy.deepcopy(macos_obs)
    del m["process"]["pid_numbering_namespace"]["reason"]
    obs_shape_rejects.append(m)
    m = copy.deepcopy(macos_obs)
    m["process"]["execution_context"]["arguments_digest"]["digest"] = (
        "sha256:" + "9" * 64
    )
    obs_shape_rejects.append(m)
    m = copy.deepcopy(macos_obs)
    m["process"]["execution_context"]["arguments_digest"]["derivation"] = copy.deepcopy(
        argv_drv_ref
    )
    obs_shape_rejects.append(m)
    m = copy.deepcopy(linux_obs)
    del m["process"]["execution_context"]["arguments_digest"]["digest"]
    obs_shape_rejects.append(m)
    m = copy.deepcopy(linux_obs)
    del m["process"]["execution_context"]["arguments_digest"]["derivation"]
    obs_shape_rejects.append(m)
    m = copy.deepcopy(macos_obs)
    del m["process"]["execution_context"]["security_principal"]["principal"]
    obs_shape_rejects.append(m)
    m = copy.deepcopy(macos_obs)
    del m["process"]["execution_context"]["security_principal"]["derivation"]
    obs_shape_rejects.append(m)
    m = copy.deepcopy(macos_obs)
    m["process"]["execution_context"]["security_principal"] = {
        "status": "inaccessible",
        "principal": {"namespace": "example.test/uid", "value": "501"},
        "reason": "denied",
    }
    obs_shape_rejects.append(m)
    m = copy.deepcopy(macos_obs)
    del m["observer"]["time_namespace"]
    obs_shape_rejects.append(m)
    # Invalid status label, PID sentinel/range violations, and forbidden serialized handle descriptor.
    m = copy.deepcopy(macos_obs)
    m["process"]["process_state"] = {"status": "denied", "reason": "not-in-enum"}
    obs_shape_rejects.append(m)
    for bad_pid in ("0", "-1", "01", "2147483648", "4294967295"):
        m = copy.deepcopy(macos_obs)
        m["process"]["pid"] = bad_pid
        obs_shape_rejects.append(m)
    m = copy.deepcopy(linux_obs)
    m["process"]["pidfd"] = "7"
    obs_shape_rejects.append(m)
    for bad_obs in obs_shape_rejects:
        shape(bad_obs, obs_schema_path, accepted=False)

    # Strict policy validation negative controls (entarch E1 + secrev + devrev H1/DR-NPO-R1-1).
    default_policy = {
        "baseline_host_scope_trusted": True,
        "candidate_host_scope_trusted": True,
        "require_live": True,
        "required_context_facts": ("security_principal",),
        "detect_observed_context_drift": True,
    }
    invalid_policies = [
        {},
        None,
        {k: v for k, v in default_policy.items() if k != "baseline_host_scope_trusted"},
        {
            k: v
            for k, v in default_policy.items()
            if k != "candidate_host_scope_trusted"
        },
        {**default_policy, "baseline_host_scope_trusted": None},
        {**default_policy, "baseline_host_scope_trusted": "false"},
        {**default_policy, "candidate_host_scope_trusted": 1},
        {**default_policy, "require_live": 1},
        {**default_policy, "detect_observed_context_drift": "true"},
        {**default_policy, "required_context_facts": ("unknown_fact",)},
        {**default_policy, "allowed_clone_behaviors": ()},
        {**default_policy, "allowed_clone_behaviors": ("bogus",)},
        {**default_policy, "unexpected_extra_key": True},
    ]
    for bad_pol in invalid_policies:
        require(
            compare_native_observations(
                linux_obs,
                copy.deepcopy(linux_obs),
                bad_pol,
                obs_profile,
                obs_profile_ref,
            )
            == "insufficient:invalid-evaluation-policy",
            f"accepted invalid comparison policy: {bad_pol!r}",
        )

    obs_comparison_cases = []
    obs_comparison_cases.append(
        ("macos-match", macos_obs, copy.deepcopy(macos_obs), default_policy, "match")
    )
    obs_comparison_cases.append(
        ("linux-match", linux_obs, copy.deepcopy(linux_obs), default_policy, "match")
    )
    # Profile mismatch returns structured code rather than raising (devrev M1).
    c = copy.deepcopy(macos_obs)
    c["profile"]["revision"] = "sha256:" + "0" * 64
    obs_comparison_cases.append(
        (
            "profile-revision-mismatch",
            macos_obs,
            c,
            default_policy,
            "insufficient:unsupported-evidence-profile",
        )
    )
    # Cross-field platform vs start_identity subprofile mismatch (devrev L1).
    c = copy.deepcopy(linux_obs)
    c["observer"]["platform_family"] = "macos"
    obs_comparison_cases.append(
        (
            "observer-platform-subprofile-mismatch",
            linux_obs,
            c,
            default_policy,
            "insufficient:inconsistent-observation",
        )
    )
    # Sub-second / microsecond and monotonic-tick native precision (no 2s tolerance).
    c = copy.deepcopy(macos_obs)
    c["process"]["start_identity"]["value"] = "1761739170.123457"
    obs_comparison_cases.append(
        (
            "macos-1us-diff",
            macos_obs,
            c,
            default_policy,
            "mismatch:start-identity-mismatch",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["process"]["start_identity"]["value"] = "987654322"
    obs_comparison_cases.append(
        (
            "linux-1tick-diff",
            linux_obs,
            c,
            default_policy,
            "mismatch:start-identity-mismatch",
        )
    )
    # Grammar-before-equality on boot_id and start_identity (devrev M1).
    c = copy.deepcopy(macos_obs)
    c["process"]["boot_id"]["value"] = "NOT-A-VALID-LOWERCASE-UUID"
    obs_comparison_cases.append(
        (
            "invalid-boot-id-before-diff",
            macos_obs,
            c,
            default_policy,
            "insufficient:invalid-boot-id",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["process"]["start_identity"]["value"] = "18446744073709551616"
    obs_comparison_cases.append(
        (
            "invalid-u64-overflow-start-identity",
            linux_obs,
            c,
            default_policy,
            "insufficient:invalid-start-identity",
        )
    )
    # Cross-profile comparison: host/boot diff -> Mismatch; same host+boot -> Insufficient (never macOS wildcard).
    obs_comparison_cases.append(
        (
            "cross-profile-diff-boot",
            macos_obs,
            linux_obs,
            default_policy,
            "mismatch:boot-id-mismatch",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["process"]["boot_id"]["value"] = macos_obs["process"]["boot_id"]["value"]
    obs_comparison_cases.append(
        (
            "cross-profile-same-boot",
            macos_obs,
            c,
            default_policy,
            "insufficient:incompatible-start-identity-profile",
        )
    )
    # Linux PID numbering namespace, observer time namespace (SR-NPO-R1-3), and target PID namespace controls.
    c = copy.deepcopy(linux_obs)
    c["process"]["pid_numbering_namespace"] = {
        "status": "error",
        "reason": "procfs overmount EXDEV on /proc/<pid>",
    }
    obs_comparison_cases.append(
        (
            "linux-overmount-or-unverified-numbering-ns",
            linux_obs,
            c,
            default_policy,
            "insufficient:missing-pid-numbering-namespace",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["process"]["pid_numbering_namespace"]["value"] = "pidns:4:4026531836"
    obs_comparison_cases.append(
        (
            "linux-malformed-pidns-missing-minor",
            linux_obs,
            c,
            default_policy,
            "insufficient:invalid-pid-namespace",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["process"]["pid_numbering_namespace"]["value"] = "pidns:0:4:4026532200"
    obs_comparison_cases.append(
        (
            "linux-numbering-view-mismatch",
            linux_obs,
            c,
            default_policy,
            "insufficient:pid-numbering-namespace-mismatch",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["observer"]["time_namespace"] = {
        "status": "observed",
        "value": "timens:0:4:4026532999",
    }
    obs_comparison_cases.append(
        (
            "linux-observer-timens-offset-mismatch",
            linux_obs,
            c,
            default_policy,
            "insufficient:observer-time-namespace-mismatch",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["process"]["target_pid_namespace"] = {
        "status": "inaccessible",
        "reason": "ptrace_may_access denied /proc/<pid>/ns/pid",
    }
    obs_comparison_cases.append(
        (
            "linux-inaccessible-target-ns",
            linux_obs,
            c,
            default_policy,
            "insufficient:missing-target-pid-namespace",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["process"]["target_pid_namespace"]["value"] = "pidns:0:4:4026532200"
    obs_comparison_cases.append(
        (
            "linux-target-ns-mismatch",
            linux_obs,
            c,
            default_policy,
            "mismatch:target-pid-namespace-mismatch",
        )
    )
    # Per-observation HostScope distrust, clone policy, metadata consistency, and reinstall mismatch (devrev M7 + entarch E2).
    obs_comparison_cases.append(
        (
            "untrusted-candidate-host-scope",
            macos_obs,
            copy.deepcopy(macos_obs),
            {**default_policy, "candidate_host_scope_trusted": False},
            "insufficient:unestablished-host-scope",
        )
    )
    obs_comparison_cases.append(
        (
            "disallowed-copyable-clone-behavior",
            macos_obs,
            copy.deepcopy(macos_obs),
            {
                **default_policy,
                "allowed_clone_behaviors": ("regenerated", "device-bound"),
            },
            "insufficient:disallowed-clone-behavior",
        )
    )
    c = copy.deepcopy(macos_obs)
    c["process"]["host_scope"]["clone_behavior"] = "regenerated"
    obs_comparison_cases.append(
        (
            "inconsistent-host-scope-clone-metadata",
            macos_obs,
            c,
            default_policy,
            "insufficient:inconsistent-host-scope-metadata",
        )
    )
    for bad_stability in ("unknown", "process"):
        c = copy.deepcopy(macos_obs)
        c["process"]["host_scope"]["stability"] = bad_stability
        obs_comparison_cases.append(
            (
                f"host-scope-stability-{bad_stability}",
                macos_obs,
                c,
                default_policy,
                "insufficient:unestablished-host-scope",
            )
        )
    c = copy.deepcopy(macos_obs)
    c["process"]["host_scope"]["value"] = "reinstalled-host-b"
    obs_comparison_cases.append(
        (
            "host-scope-reinstall-mismatch",
            macos_obs,
            c,
            default_policy,
            "mismatch:host-scope-mismatch",
        )
    )
    # Distinct exited target (`not-present`) vs lost visibility (`inaccessible`/`error`/`unknown`) vs zombie (devrev M2).
    c = copy.deepcopy(macos_obs)
    c["process"]["process_state"] = {
        "status": "not-present",
        "reason": "target-pid-absent",
    }
    c["process"]["start_identity"] = {
        "status": "not-present",
        "profile": copy.deepcopy(macos_obs["process"]["start_identity"]["profile"]),
        "reason": "target-pid-absent",
    }
    obs_comparison_cases.append(
        (
            "candidate-process-exited",
            macos_obs,
            c,
            default_policy,
            "mismatch:process-exited",
        )
    )
    c = copy.deepcopy(macos_obs)
    c["observer"]["bracketed"] = False
    obs_comparison_cases.append(
        (
            "unbracketed-candidate",
            macos_obs,
            c,
            default_policy,
            "insufficient:unbracketed-observation",
        )
    )
    c = copy.deepcopy(macos_obs)
    c["process"]["process_state"]["value"] = "zombie"
    obs_comparison_cases.append(
        ("zombie-candidate", macos_obs, c, default_policy, "mismatch:process-not-live")
    )
    for state_err in ("inaccessible", "error", "unknown"):
        c = copy.deepcopy(macos_obs)
        c["process"]["process_state"] = {
            "status": state_err,
            "reason": f"state-{state_err}",
        }
        obs_comparison_cases.append(
            (
                f"state-{state_err}",
                macos_obs,
                c,
                default_policy,
                "insufficient:missing-process-state",
            )
        )
    c = copy.deepcopy(macos_obs)
    c["observer"]["platform_family"] = "windows"
    c["process"]["start_identity"]["profile"]["id"] = (
        "urn:3leaps:identity-evidence:start-identity:windows-filetime:v0"
    )
    c["process"]["start_identity"]["value"] = "134062128000000000"
    obs_comparison_cases.append(
        (
            "reserved-windows-subprofile",
            c,
            copy.deepcopy(c),
            default_policy,
            "insufficient:unsupported-start-identity-profile",
        )
    )
    # Context derivation refusal, derivation mismatch, canonical order independence (M3 / DR-NPO-R1-6), and drift.
    c = copy.deepcopy(macos_obs)
    c["process"]["execution_context"]["security_context_digest"] = {
        "status": "observed",
        "derivation": {
            "id": "urn:3leaps:identity-evidence:context-derivation:macos-secctx-deferred:v0",
            "revision": obs_readme_digest,
        },
        "digest": "sha256:" + "b" * 64,
    }
    obs_comparison_cases.append(
        (
            "deferred-macos-secctx-derivation-refused",
            macos_obs,
            c,
            default_policy,
            "insufficient:unsupported-context-derivation-security_context_digest",
        )
    )
    c = copy.deepcopy(linux_obs)
    c["process"]["execution_context"]["arguments_digest"]["digest"] = (
        "sha256:" + "f" * 64
    )
    obs_comparison_cases.append(
        (
            "linux-arguments-drift",
            linux_obs,
            c,
            default_policy,
            "mismatch:context-changed-arguments_digest",
        )
    )
    # Observed context derivation incompatibility between two accepted revisions/derivations (Step 8c).
    alt_obs_profile = copy.deepcopy(obs_profile)
    alt_obs_profile["context_derivations"]["arguments_digest"][
        "urn:3leaps:identity-evidence:context-derivation:argv-bytes-alt:v0"
    ] = copy.deepcopy(
        obs_profile["context_derivations"]["arguments_digest"][
            "urn:3leaps:identity-evidence:context-derivation:argv-bytes:v0"
        ]
    )
    c_alt_drv = copy.deepcopy(linux_obs)
    c_alt_drv["process"]["execution_context"]["arguments_digest"]["derivation"][
        "id"
    ] = "urn:3leaps:identity-evidence:context-derivation:argv-bytes-alt:v0"
    shape(c_alt_drv, obs_schema_path)
    require(
        compare_native_observations(
            linux_obs,
            c_alt_drv,
            default_policy,
            alt_obs_profile,
            obs_profile_ref,
        )
        == "insufficient:incompatible-context-derivation-arguments_digest",
        "failed to refuse incompatible observed context derivation",
    )
    # Simultaneous changed arguments_digest + missing executable_digest: both list orders return missing executable_digest!
    c_simul = copy.deepcopy(linux_obs)
    c_simul["process"]["execution_context"]["arguments_digest"]["digest"] = (
        "sha256:" + "f" * 64
    )
    c_simul["process"]["execution_context"]["executable_digest"] = {
        "status": "inaccessible",
        "reason": "exe unreadable",
    }
    for order_label, req_order in (
        ("exe-then-args", ("executable_digest", "arguments_digest")),
        ("args-then-exe", ("arguments_digest", "executable_digest")),
    ):
        obs_comparison_cases.append(
            (
                f"canonical-context-precedence-{order_label}",
                linux_obs,
                c_simul,
                {**default_policy, "required_context_facts": req_order},
                "insufficient:missing-context-executable_digest",
            )
        )
    obs_comparison_cases.append(
        (
            "macos-required-unprobed-arguments",
            macos_obs,
            copy.deepcopy(macos_obs),
            {**default_policy, "required_context_facts": ("arguments_digest",)},
            "insufficient:missing-context-arguments_digest",
        )
    )
    for case_id, b_obs, c_obs, pol, expected in obs_comparison_cases:
        shape(b_obs, obs_schema_path)
        shape(c_obs, obs_schema_path)
        got = compare_native_observations(
            b_obs, c_obs, pol, obs_profile, obs_profile_ref
        )
        require(
            got == expected,
            f"native comparison {case_id}: got {got}, expected {expected}",
        )

    # End-to-end projection + input_reports provenance into local-process-session:v0.
    live_now = "2026-10-29T12:00:02Z"
    linux_obs_report = copy.deepcopy(examples["native-process-observation"])
    linux_obs_report["report_id"] = "native-process-observation-linux"
    linux_obs_report["evidence"][0].update(
        source="synthetic-linux-procfs-fixture",
        digest=fixture_digest(linux_obs),
    )
    linux_obs_report["capabilities"] = [
        {
            "id": "cap-pidfd-handle",
            "subject_ref": "process-a",
            "provider": "linux-pidfd",
            "capability": "process-continuity-handle",
            "status": "available",
            "reason": "Private pidfd_open(pid, 0) handle bracketed by procfs stat and namespace checks.",
            "observed_at": "2026-10-29T12:00:00Z",
        }
    ]
    shape(linux_obs_report, FAMILY / "report.schema.json")
    necessary_conditions(linux_obs_report)
    bind_native_observation_report(linux_obs_report, linux_obs, obs_profile_ref)

    projected_proc = project_to_local_process_session_process(
        linux_obs,
        True,
        live_now,
        obs_profile,
        obs_profile_ref,
        report=linux_obs_report,
    )
    # Host-scope collision & 512-byte boundary controls (entarch E2 + secrev SR-NPO-R1-2 + devrev DR-NPO-R1-2/3).
    slash_a = copy.deepcopy(linux_obs)
    slash_a["process"]["host_scope"].update(namespace="example.test/a", value="b/c")
    slash_b = copy.deepcopy(linux_obs)
    slash_b["process"]["host_scope"].update(namespace="example.test/a/b", value="c")
    rev_c = copy.deepcopy(linux_obs)
    rev_c["process"]["host_scope"]["derivation"]["revision"] = "sha256:" + "e" * 64
    max_len_obs = copy.deepcopy(linux_obs)
    max_len_obs["process"]["host_scope"].update(namespace="n" * 512, value="v" * 512)
    shape(slash_a, obs_schema_path)
    shape(slash_b, obs_schema_path)
    shape(rev_c, obs_schema_path)
    shape(max_len_obs, obs_schema_path)
    proj_slash_a = project_to_local_process_session_process(
        slash_a, True, live_now, obs_profile, obs_profile_ref
    )
    proj_slash_b = project_to_local_process_session_process(
        slash_b, True, live_now, obs_profile, obs_profile_ref
    )
    proj_rev_c = project_to_local_process_session_process(
        rev_c, True, live_now, obs_profile, obs_profile_ref
    )
    proj_max_len = project_to_local_process_session_process(
        max_len_obs, True, live_now, obs_profile, obs_profile_ref
    )
    require(
        fixture_digest(proj_slash_a) != fixture_digest(proj_slash_b)
        and fixture_digest(projected_proc) != fixture_digest(proj_rev_c)
        and len(proj_max_len["host_scope"]) == 114,
        "host-scope-projection-collision-or-length-violation",
    )
    max_len_bundle = copy.deepcopy(bundle)
    max_len_bundle["process"] = proj_max_len
    shape(max_len_bundle, process_root / "evidence.schema.json")

    composed_bundle = copy.deepcopy(bundle)
    composed_bundle["process"] = projected_proc
    composed_bundle["launch"]["process_digest"] = fixture_digest(projected_proc)
    composed_receipt_digest = fixture_digest(composed_bundle["launch"])
    composed_bundle["challenge"]["receipt_digest"] = composed_receipt_digest
    composed_transcript = {
        "domain": profile["transcript_domain"],
        "profile": profile_ref,
        "process_digest": fixture_digest(projected_proc),
        "session_digest": fixture_digest(composed_bundle["session"]),
        "receipt_digest": composed_receipt_digest,
        "challenge": composed_bundle["challenge"],
    }
    composed_transcript_digest = fixture_digest(composed_transcript)
    composed_bundle["proof"]["transcript_digest"] = composed_transcript_digest
    shape(composed_bundle, process_root / "evidence.schema.json")

    composed_report = copy.deepcopy(examples["local-process-session-launch"])
    composed_report["report_id"] = "composed-local-process-session-launch"
    composed_report["subjects"].append({"id": "host-a", "kind": "os-installation"})
    composed_report["identifiers"].append(
        copy.deepcopy(linux_obs_report["identifiers"][0])
    )
    composed_report["input_reports"] = [
        {
            "id": "source-native-observation",
            "report_id": linux_obs_report["report_id"],
            "digest": fixture_digest(linux_obs_report),
        }
    ]
    imported_ev = copy.deepcopy(linux_obs_report["evidence"][0])
    imported_ev["origin"] = {
        "input_ref": "source-native-observation",
        "record_ref": imported_ev["id"],
    }
    composed_report["evidence"].append(imported_ev)
    for ev in composed_report["evidence"]:
        if ev["format_profile"] == profile_ref:
            ev["digest"] = fixture_digest(composed_bundle)
    composed_ctx = copy.deepcopy(original_context)
    composed_ctx["current_process"] = copy.deepcopy(projected_proc)
    composed_ctx["verified_receipt_digest"] = composed_receipt_digest
    composed_ctx["verified_transcript_digest"] = composed_transcript_digest
    shape(composed_report, FAMILY / "report.schema.json")
    necessary_conditions(
        composed_report, {linux_obs_report["report_id"]: linux_obs_report}
    )
    process_session_fit(
        composed_report, composed_bundle, composed_ctx, profile, profile_ref
    )

    # Fail-closed projection negative controls (no invented digests, no truthy non-bool, no stale bypass).
    projection_refusals = [
        (macos_obs, True, live_now, "missing-pid-namespace-for-session-bundle"),
        (linux_obs, False, live_now, "unestablished-host-scope"),
        (linux_obs, None, live_now, "invalid-evaluation-policy"),
        (linux_obs, 1, live_now, "invalid-evaluation-policy"),
        (linux_obs, "true", live_now, "invalid-evaluation-policy"),
        (linux_obs, True, "2026-10-29T12:00:06Z", "stale-process-observation"),
        (linux_obs, True, "2026-10-29T11:59:59Z", "future-process-observation"),
        (linux_obs, True, None, "trusted-clock-unavailable"),
    ]
    partial_linux = copy.deepcopy(linux_obs)
    partial_linux["process"]["execution_context"]["arguments_digest"] = {
        "status": "not-probed",
        "reason": "default opt-in policy",
    }
    projection_refusals.append(
        (
            partial_linux,
            True,
            live_now,
            "missing-context-for-session-bundle:arguments_digest",
        )
    )
    diff_ns_linux = copy.deepcopy(linux_obs)
    diff_ns_linux["process"]["pid_numbering_namespace"]["value"] = (
        "pidns:0:4:4026532200"
    )
    projection_refusals.append(
        (
            diff_ns_linux,
            True,
            live_now,
            "ambiguous-pid-namespace-for-session-bundle",
        )
    )
    for bad_proj_obs, trusted_flag, p_now, expected_err in projection_refusals:
        shape(bad_proj_obs, obs_schema_path)
        try:
            project_to_local_process_session_process(
                bad_proj_obs, trusted_flag, p_now, obs_profile, obs_profile_ref
            )
        except ValueError as exc:
            require(
                str(exc) == expected_err,
                f"projection refusal got {exc}, expected {expected_err}",
            )
        else:
            raise ValueError(f"accepted invalid session projection: {expected_err}")

    flush_shapes()
    suite_error_controls(goneat)
    print(
        f"PASS: 4 dimension definitions, {len(examples)} examples, {len(schema_mutations)} shape rejects, {len(semantic_mutations)} semantic rejects, {len(process_cases)} process fit cases (+13 boundary/refusal controls), {len(obs_shape_rejects)} native-obs shape rejects, {len(obs_comparison_cases)} native-obs comparison cases, {len(projection_refusals) + 1} session projection controls, 6 time shape refusals, 5 time binding/provenance refusals, two-producer collision, 7 capability states, stale history, batched suite error controls"
    )
    print(
        "Logical draft controls only; no native, cryptographic, policy or twin implementation qualification."
    )


if __name__ == "__main__":
    main()
