#!/usr/bin/env python3
"""Validate the application-control v0 manifest and semantic fixture layer."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import pathlib
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parent.parent
FAMILY = REPO / "schemas/application-control/v0"
FIXTURES = FAMILY / "fixtures"
ARTIFACTS = {
    "application-descriptor": FAMILY / "application-descriptor.schema.json",
    "operation-catalog": FAMILY / "operation-catalog.schema.json",
    "information-source-catalog": (FAMILY / "information-source-catalog.schema.json"),
    "control-message": FAMILY / "control-message.schema.json",
    "observation-message": FAMILY / "observation-message.schema.json",
    "control-evidence": FAMILY / "control-evidence.schema.json",
    "control-policy": FAMILY / "control-policy.schema.json",
}
SEMANTIC_LAYER_ID = "application-control/v0-semantics"
SEMANTIC_LAYER_VERSION = "0.2.0"
FINGERPRINT_DOMAIN = b"application-control/v0/request-fingerprint\x00"
MAX_SAFE_INTEGER = 9007199254740991

failures: list[str] = []


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object member: {key}")
        result[key] = value
    return result


def load(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def fail(message: str) -> None:
    failures.append(message)
    print(f"FAIL {message}")


def ok(message: str) -> None:
    print(f"ok   {message}")


def parse_datetime(value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def duplicate(values: list[Any]) -> bool:
    return len(values) != len(set(values))


def canonical_json_v0(value: Any) -> bytes:
    """Return the contract's canonical JSON v0 bytes.

    The control profile deliberately accepts only null, booleans, strings,
    safe integers, arrays, and string-keyed objects. This keeps the portable
    fingerprint algorithm exact without depending on a language's float
    serializer.
    """

    def validate(item: Any) -> None:
        if item is None or isinstance(item, (bool, str)):
            return
        if isinstance(item, int):
            if abs(item) > MAX_SAFE_INTEGER:
                raise ValueError("integer outside interoperable range")
            return
        if isinstance(item, list):
            for child in item:
                validate(child)
            return
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ValueError("object key is not a string")
            for key, child in item.items():
                key.encode("utf-8")
                validate(child)
            return
        raise ValueError("fractional numbers are not canonical JSON v0")

    validate(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def request_projection(request: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in request.items()
        if key not in {"request_id", "request_fingerprint"}
    }


def request_fingerprint(request: dict[str, Any]) -> str:
    return hashlib.sha256(
        FINGERPRINT_DOMAIN + canonical_json_v0(request_projection(request))
    ).hexdigest()


def fingerprint_matches(claim: Any, request: dict[str, Any]) -> bool:
    return isinstance(claim, str) and hmac.compare_digest(
        claim, request_fingerprint(request)
    )


try:
    json.loads('{"duplicate":1,"duplicate":2}', object_pairs_hook=unique_object)
except ValueError:
    ok("canonical JSON duplicate-member rejection")
else:
    fail("canonical JSON duplicate-member rejection is not enforced")


def semantic_violations(bundle: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    descriptor = bundle["descriptor"]
    operations_doc = bundle["operation_catalog"]
    sources_doc = bundle["information_source_catalog"]
    policy = bundle["policy"]
    request = bundle["request"]
    result = bundle["result"]
    observation = bundle["observation"]
    evidence = bundle["evidence"]
    replay_request = bundle.get("replay_request")

    operations = operations_doc.get("operations", [])
    sources = sources_doc.get("sources", [])
    rules = policy.get("rules", [])
    operation_ids = [item.get("operation_id") for item in operations]
    source_ids = [item.get("source_id") for item in sources]
    rule_ids = [item.get("rule_id") for item in rules]
    non_controlled = [
        item.get("surface_ref")
        for item in operations_doc.get("non_controllable_surfaces", [])
    ]
    if any(
        duplicate(values)
        for values in (operation_ids, source_ids, rule_ids, non_controlled)
    ):
        violations.append("SEM-C01")

    control_surfaces = [
        surface for item in operations for surface in item.get("surface_refs", [])
    ]
    if duplicate(control_surfaces) or set(control_surfaces).intersection(
        non_controlled
    ):
        violations.append("SEM-C02")
    information_surfaces = [
        surface for item in sources for surface in item.get("surface_refs", [])
    ]
    if duplicate(information_surfaces):
        violations.append("SEM-C03")

    application = descriptor.get("application")
    if (
        operations_doc.get("application") != application
        or sources_doc.get("application") != application
        or request.get("application") != application
        or result.get("application") != application
        or observation.get("application") != application
        or evidence.get("application") != application
        or any(application not in rule.get("applications", []) for rule in rules)
    ):
        violations.append("SEM-C12")

    operation_by_id = {item.get("operation_id"): item for item in operations}
    source_by_id = {item.get("source_id"): item for item in sources}
    operation = operation_by_id.get(request.get("operation_id"))
    if operation is None or request.get("target", {}).get("kind") != operation.get(
        "target_kind"
    ):
        violations.append("SEM-C04")
    else:
        expected = operation.get("request", {})
        actual = request.get("payload", {})
        if actual.get("schema") != expected.get("schema") or actual.get(
            "sha256"
        ) != expected.get("sha256"):
            violations.append("SEM-C05")
        if operation.get("effect") in {"mutate", "destructive"}:
            required = {
                "idempotency_key",
                "request_fingerprint",
            }
            if not required.issubset(request):
                violations.append("SEM-C06")
            else:
                try:
                    if not fingerprint_matches(
                        request.get("request_fingerprint"), request
                    ):
                        violations.append("SEM-C17")
                except (TypeError, UnicodeError, ValueError):
                    violations.append("SEM-C17")
            if (
                operation.get("precondition") == "generation_required"
                and "expected_generation" not in request
            ):
                violations.append("SEM-C06")

    if isinstance(replay_request, dict):
        try:
            replay_claim_valid = fingerprint_matches(
                replay_request.get("request_fingerprint"), replay_request
            )
        except (TypeError, UnicodeError, ValueError):
            replay_claim_valid = False
        if not replay_claim_valid:
            violations.append("SEM-C17")
        if replay_request.get("idempotency_key") == request.get("idempotency_key"):
            try:
                same_projection = canonical_json_v0(
                    request_projection(replay_request)
                ) == canonical_json_v0(request_projection(request))
            except (TypeError, UnicodeError, ValueError):
                same_projection = False
            if not same_projection or replay_request.get(
                "request_fingerprint"
            ) != request.get("request_fingerprint"):
                violations.append("SEM-C07")

    result_operation = operation_by_id.get(result.get("operation_id"))
    if result_operation:
        expected = result_operation.get("result", {})
        actual = result.get("payload", {})
        if actual.get("schema") != expected.get("schema") or actual.get(
            "sha256"
        ) != expected.get("sha256"):
            violations.append("SEM-C05")
    if result.get("decision") in {"denied", "confirmation_required"} and (
        result.get("effect") != "not_applied"
    ):
        violations.append("SEM-C08")
    descriptor_policy = descriptor.get("policy")
    policy_hash = bundle.get("_artifact_sha256", {}).get("policy")
    policy_correlation = {
        "id": policy.get("policy_id"),
        "version": policy.get("policy_version"),
        "sha256": policy_hash,
    }
    if (
        any(
            result.get(field) != request.get(field)
            for field in (
                "request_id",
                "application",
                "instance_id",
                "operation_id",
            )
        )
        or not isinstance(descriptor_policy, dict)
        or descriptor_policy.get("sha256") != policy_hash
        or result.get("target") != request.get("target")
        or result.get("policy") != policy_correlation
        or (
            "expected_generation" in request
            and result.get("generation_before") != request.get("expected_generation")
        )
        or not isinstance(result.get("generation_after"), int)
        or result.get("generation_after", 0) < result.get("generation_before", 0)
    ):
        violations.append("SEM-C08")
    if result_operation and result_operation.get("idempotency") == "required":
        if any(
            result.get(field) != request.get(field)
            for field in ("idempotency_key", "request_fingerprint")
        ):
            violations.append("SEM-C08")

    source = source_by_id.get(observation.get("source_id"))
    if source is None:
        violations.append("SEM-C09")
    else:
        payload = observation.get("payload", {})
        expected = source.get("payload", {})
        provenance = observation.get("provenance", {})
        if (
            source.get("mode") not in {"event", "snapshot", "sample"}
            or observation.get("mode") != source.get("mode")
            or payload.get("schema") != expected.get("schema")
            or payload.get("sha256") != expected.get("sha256")
            or provenance.get("source") != source.get("provenance")
            or observation.get("consumer_kind")
            not in source.get("eligible_consumers", [])
        ):
            violations.append("SEM-C09")
        delivery = source.get("delivery", {})
        if source.get("mode") == "event" and (
            delivery.get("ordering") == "not_applicable"
            or delivery.get("coalescing") == "not_applicable"
            or delivery.get("gap") == "not_applicable"
            or "sequence" not in observation
            or "gap" not in observation
        ):
            violations.append("SEM-C09")
        if source.get("mode") != "event" and (
            delivery.get("ordering") != "not_applicable"
            or delivery.get("gap") != "not_applicable"
        ):
            violations.append("SEM-C09")
        if source.get("replay") != "none" and "cursor" not in observation:
            violations.append("SEM-C10")
    try:
        if parse_datetime(observation["recorded_at"]) < parse_datetime(
            observation["occurred_at"]
        ):
            violations.append("SEM-C10")
    except (KeyError, TypeError, ValueError):
        pass

    for item in operations:
        if not set(item.get("emitted_sources", [])).issubset(source_by_id):
            violations.append("SEM-C11")
            break

    target_kinds = {item.get("target_kind") for item in operations}
    for rule in rules:
        if rule.get("kind") == "control" and (
            not set(rule.get("operations", [])).issubset(operation_by_id)
            or not all(
                target.get("kind") in target_kinds for target in rule.get("targets", [])
            )
        ):
            violations.append("SEM-C12")
            break
        if rule.get("kind") == "observe" and not set(
            rule.get("information_sources", [])
        ).issubset(source_by_id):
            violations.append("SEM-C12")
            break
        if rule.get("kind") == "observe":
            capabilities = set(rule.get("capabilities", []))
            if any(
                source_by_id[source_id].get("required_capability") not in capabilities
                for source_id in rule.get("information_sources", [])
                if source_id in source_by_id
            ):
                violations.append("SEM-C12")
                break

    valid_evidence_sources = {
        "interaction": "user_interface",
        "request": "authenticated_adapter",
        "decision": "policy_engine",
        "effect": "application",
    }
    if valid_evidence_sources.get(evidence.get("stage")) != evidence.get("source"):
        violations.append("SEM-C14")
    if any(
        evidence.get(field) != request.get(field)
        for field in (
            "request_id",
            "application",
            "instance_id",
            "operation_id",
        )
    ):
        violations.append("SEM-C14")
    if evidence.get("target") != request.get("target"):
        violations.append("SEM-C14")
    stage = evidence.get("stage")
    if stage in {"request", "decision", "effect"} and (
        evidence.get("principal_ref") != result.get("principal_ref")
    ):
        violations.append("SEM-C14")
    if (
        operation
        and operation.get("idempotency") == "required"
        and stage
        in {
            "request",
            "decision",
            "effect",
        }
    ):
        if any(
            evidence.get(field) != request.get(field)
            for field in ("idempotency_key", "request_fingerprint")
        ):
            violations.append("SEM-C14")
    if stage in {"decision", "effect"} and evidence.get("policy") != result.get(
        "policy"
    ):
        violations.append("SEM-C14")
    if stage == "effect" and any(
        evidence.get(field) != result.get(field)
        for field in ("generation_before", "generation_after")
    ):
        violations.append("SEM-C14")
    evidence_operation = operation_by_id.get(evidence.get("operation_id"), {})
    evidence_contract = evidence_operation.get("evidence", {}).get(stage, {})
    evidence_fact = evidence.get("fact", {})
    if evidence_fact.get("schema") != evidence_contract.get(
        "schema"
    ) or evidence_fact.get("sha256") != evidence_contract.get("sha256"):
        violations.append("SEM-C14")
    if evidence.get("stage") == "interaction":
        if evidence.get("surface_ref") not in evidence_operation.get(
            "surface_refs", []
        ):
            violations.append("SEM-C14")
    elif "surface_ref" in evidence:
        violations.append("SEM-C14")
    try:
        if parse_datetime(evidence["recorded_at"]) < parse_datetime(
            evidence["occurred_at"]
        ):
            violations.append("SEM-C10")
    except (KeyError, TypeError, ValueError):
        pass

    if (
        descriptor.get("control_endpoint") is not None
        and descriptor.get("policy") is None
    ):
        violations.append("SEM-C15")

    hashes = bundle.get("_artifact_sha256", {})
    descriptor_refs = {
        "operation_catalog": descriptor.get("operation_catalog"),
        "information_source_catalog": descriptor.get("information_source_catalog"),
        "policy": descriptor.get("policy"),
    }
    if any(
        not isinstance(ref, dict) or ref.get("sha256") != hashes.get(name)
        for name, ref in descriptor_refs.items()
    ):
        violations.append("SEM-C16")

    return sorted(set(violations))


manifest = load(FAMILY / "contract.json")
if (
    manifest.get("capability") != "contract: application-control/v0"
    or manifest.get("entry_schema") != "application-descriptor.schema.json"
    or manifest.get("status") != "proposed"
    or set(manifest.get("object_schemas", {}).values())
    != {path.name for key, path in ARTIFACTS.items() if key != "application-descriptor"}
):
    fail("contract.json does not declare the expected application-control family")
else:
    ok("contract manifest")

for schema_path in ARTIFACTS.values():
    schema = load(schema_path)
    expected_id = f"contract:application-control/v0/{schema_path.name}"
    if schema.get("$id") != expected_id:
        fail(f"{schema_path.name}: expected $id {expected_id}")
    else:
        ok(f"schema identity {schema_path.name}")

semantic_manifest = load(FIXTURES / "semantic/manifest.json")
layer = semantic_manifest.get("semantic_layer", {})
if layer != {"id": SEMANTIC_LAYER_ID, "version": SEMANTIC_LAYER_VERSION}:
    fail(f"semantic manifest declares unexpected layer {layer}")
else:
    ok(f"semantic layer {SEMANTIC_LAYER_ID} {SEMANTIC_LAYER_VERSION}")


def resolve_bundle(path: pathlib.Path) -> dict[str, Any]:
    refs = load(path)
    paths = {key: (path.parent / ref).resolve() for key, ref in refs.items()}
    bundle = {key: load(artifact_path) for key, artifact_path in paths.items()}
    bundle["_artifact_sha256"] = {
        key: hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        for key, artifact_path in paths.items()
        if key in {"operation_catalog", "information_source_catalog", "policy"}
    }
    return bundle


base_path = FIXTURES / "semantic/conforming" / "complete-workbench.json"
base_bundle = resolve_bundle(base_path)
for name in semantic_manifest.get("conforming", []):
    path = FIXTURES / "semantic/conforming" / name
    violations = semantic_violations(resolve_bundle(path))
    if violations:
        fail(f"semantic conforming {name}: {violations}")
    else:
        ok(f"semantic conforming {name}")

for name, expected_rule in semantic_manifest.get("negative", {}).items():
    path = FIXTURES / "semantic/negative" / name
    case = load(path)
    bundle = dict(base_bundle)
    replacement_path = (path.parent / case["fixture"]).resolve()
    bundle[case["replace"]] = load(replacement_path)
    if case["replace"] in {
        "operation_catalog",
        "information_source_catalog",
        "policy",
    }:
        bundle["_artifact_sha256"] = dict(bundle["_artifact_sha256"])
        bundle["_artifact_sha256"][case["replace"]] = hashlib.sha256(
            replacement_path.read_bytes()
        ).hexdigest()
    violations = semantic_violations(bundle)
    if expected_rule in violations:
        ok(f"semantic negative {name} (violates {expected_rule})")
    else:
        fail(f"semantic negative {name}: expected {expected_rule}, got {violations}")

listed = set(semantic_manifest.get("negative", {}))
found = {path.name for path in (FIXTURES / "semantic/negative").glob("*.json")}
if listed != found:
    fail(
        "semantic manifest / fixture drift: "
        f"listed={sorted(listed)} found={sorted(found)}"
    )

if failures:
    print(f"\n{len(failures)} failure(s)")
    sys.exit(1)

print("\nApplication control v0 manifest and semantic fixtures: OK")
