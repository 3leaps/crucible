#!/usr/bin/env python3
"""Synthetic shape/pin/semantic controls; no runtime or authority qualification.

Invocation set (PDR-0006): Python 3 stdlib and goneat JSON Schema validation.
No network requests or instance-selected executable/schema paths are used.

Fixtures on disk are the vectors. Schema rejects live in rejects/schema/ as
reject-<object>--<name>.json. Semantic rejects live in rejects/semantic/ as
reject-<reason>--<name>/ directories holding only the objects that differ from
the baseline; an absent object is the corresponding file in examples/.
"""

import copy
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "schemas/data-acquisition/v0"
EXAMPLES = BASE / "examples"
REJECTS = BASE / "rejects"
STANDARD = ROOT / "docs/standards/data-acquisition-contract.md"
KINDS = ("source-policy", "acquisition-plan", "registration-result")
BASELINE = {
    "source-policy": EXAMPLES / "source-policy.json",
    "acquisition-plan": EXAMPLES / "acquisition-plan.json",
}


class Refusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def strict_load(raw):
    def pairs(items):
        keys = [k for k, _ in items]
        require(len(keys) == len(set(keys)), "duplicate_key")
        return dict(items)

    return json.loads(raw, object_pairs_hook=pairs)


def instant(value):
    try:
        require(value.endswith("Z"), "utc_required")
        return dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except (ValueError, TypeError):
        raise Refusal("invalid_time")


def encoded(value):
    return (json.dumps(value, indent=2) + "\n").encode()


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def same_scope(a, b):
    return (
        set(a["target_ids"]) == set(b["target_ids"])
        and a["time_scope"] == b["time_scope"]
    )


def ceiling(meter, headroom_bps, interval):
    """Most a rolling-window meter can admit in interval, after headroom."""
    usable = meter["limit"] * (10000 - headroom_bps) // 10000
    windows = -(-interval // dt.timedelta(seconds=meter["window_seconds"]))
    return usable * windows


def semantic(policy, plan, result, policy_bytes, plan_bytes):
    start = instant(plan["start_at"])
    created = instant(plan["created_at"])
    require(created <= start, "plan_time_order")
    terms = policy["access_terms"]
    require(terms["current_digest"] == terms["reviewed_digest"], "terms_changed")
    require(
        instant(terms["reviewed_at"]) <= start
        and instant(policy["meter_review"]["reviewed_at"]) <= start,
        "review_after_start",
    )
    meters = policy["meters"]
    require(
        set(policy["meter_review"]["unconfigured"])
        == {name for name in ("body_bytes", "errors") if name not in meters},
        "unreviewed_meter_absence",
    )
    for meter in meters.values():
        require(meter["limit"] > 0, "zero_meter")
        if "burst" in meter:
            require(0 < meter["burst"] <= meter["limit"], "burst_exceeds_window")
    # These controls select the response-body-only fixture profile. Transfer is
    # structurally valid, but is not qualified by this fixture consumer.
    require(
        meters.get("body_bytes", {}).get("basis", "response_body") == "response_body",
        "unsupported_meter_basis",
    )
    require(policy["transport"]["concurrency_limit"] > 0, "zero_concurrency")
    dimensions = policy["target_set"]["dimensions"]
    require(
        len({d["name"] for d in dimensions}) == len(dimensions), "duplicate_dimension"
    )
    dimensions = {d["name"]: d for d in dimensions}
    targets = policy["target_set"]["targets"]
    require(len({t["id"] for t in targets}) == len(targets), "duplicate_target")
    for target in targets:
        try:
            u = urlsplit(target["endpoint_uri"])
            _ = u.port
            require(
                u.scheme == "https"
                and u.hostname
                and not u.username
                and not u.password
                and not u.query
                and not u.fragment
                and "@" not in u.netloc,
                "unsafe_target_url",
            )
        except ValueError:
            raise Refusal("unsafe_target_url")
        for name, value in target["variants"].items():
            require(name in dimensions, "unknown_variant")
            dimension = dimensions[name]
            if dimension["kind"] == "enum":
                require(value in dimension["values"], "variant_outside_vocabulary")
            if dimension["kind"] == "timestamp":
                instant(value)
    expected_policy = {"id": policy["policy_id"], "digest": digest(policy_bytes)}
    require(plan["policy"] == expected_policy, "policy_pin_mismatch")
    require(
        plan["target_set_version"] == policy["target_set"]["version"],
        "target_set_version",
    )
    ids = {t["id"] for t in targets}
    for scope in (plan["original_scope"], plan["effective_scope"]):
        require(set(scope["target_ids"]) <= ids, "undeclared_target")
    original = plan["original_scope"]
    effective = plan["effective_scope"]
    cadence = plan.get("cadence_seconds")
    selected = plan.get("effective_cadence_seconds")
    changed = not same_scope(original, effective) or cadence != selected
    choice = plan.get("compromise")
    require(bool(choice) == changed, "compromise_required_or_spurious")
    if choice:
        require(instant(choice["chosen_at"]) <= created, "choice_after_plan")
        require(
            same_scope(choice["declared_scope_limit"], effective)
            and choice.get("effective_cadence_seconds") == selected,
            "scope_limit_mismatch",
        )
        kind = choice["kind"]
        if kind == "lower_frequency":
            require(
                plan["recurring"]
                and selected > cadence
                and same_scope(original, effective),
                "invalid_frequency_choice",
            )
        elif kind == "fewer_targets":
            require(
                set(effective["target_ids"]) < set(original["target_ids"])
                and effective["time_scope"] == original["time_scope"]
                and selected == cadence,
                "invalid_target_choice",
            )
        elif kind == "time_scope":
            require(
                set(effective["target_ids"]) == set(original["target_ids"])
                and effective["time_scope"] != original["time_scope"]
                and selected == cadence,
                "invalid_time_scope_choice",
            )
            # Actual time-scope narrowing is the work-manifest profile's job.
    if selected and "deletion_window_seconds" in policy:
        require(
            selected < policy["deletion_window_seconds"], "cadence_reaches_deletion"
        )
    headroom = policy.get("headroom_bps", 2000)
    if result:
        require(
            result["policy"] == expected_policy
            and result["entity"] == policy["entity"]
            and result["source"] == policy["source"],
            "registration_policy_binding",
        )
        require(
            result["plan"] == {"id": plan["plan_id"], "digest": digest(plan_bytes)},
            "registration_plan_binding",
        )
        require(instant(result["recorded_at"]) >= created, "registration_time_order")
        if result["outcome"] == "registered":
            a = result["allocation"]
            opens, closes = instant(a["opens_at"]), instant(a["closes_at"])
            require(closes > opens >= start, "invalid_allocation_window")
            require(a["requests"] > 0, "zero_allocation")
            require(
                all(name in a for name in ("body_bytes", "errors") if name in meters),
                "allocation_missing_meter",
            )
            require(
                all(name in meters for name in ("body_bytes", "errors") if name in a),
                "allocation_unconfigured_meter",
            )
            # One allocation alone must fit the parent ceiling. Checking all
            # overlapping allocations remains the registration authority's job.
            require(
                all(
                    a[name] <= ceiling(meters[name], headroom, closes - opens)
                    for name in meters
                ),
                "allocation_exceeds_policy",
            )
    return {
        "headroom_bps": headroom,
        "byte_basis": meters.get("body_bytes", {}).get("basis", "response_body"),
    }


def shape_file(kind, path):
    completed = subprocess.run(
        [
            "goneat",
            "validate",
            "data",
            "--schema-file",
            str(BASE / (kind + ".schema.json")),
            "--data",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def shape(kind, value):
    with tempfile.TemporaryDirectory(prefix="acquisition-control-") as tmp:
        path = pathlib.Path(tmp) / "instance.json"
        path.write_bytes(encoded(value))
        return shape_file(kind, path)


def check_case(paths):
    """Strict-load, shape-check and semantically check one case.

    Returns None on acceptance or the refusal reason. A shape failure is
    reported as "shape:<kind>" so a semantic vector cannot pass by accident.
    """
    raw = {kind: path.read_bytes() for kind, path in paths.items()}
    try:
        objects = {kind: strict_load(b) for kind, b in raw.items()}
    except Refusal as error:
        return str(error)
    for kind, path in paths.items():
        if not shape_file(kind, path):
            return "shape:" + kind
    try:
        semantic(
            objects["source-policy"],
            objects["acquisition-plan"],
            objects.get("registration-result"),
            raw["source-policy"],
            raw["acquisition-plan"],
        )
    except Refusal as error:
        return str(error)
    return None


def case_paths(directory):
    paths = dict(BASELINE)
    for kind in KINDS:
        candidate = directory / (kind + ".json")
        if candidate.exists():
            paths[kind] = candidate
    return paths


def diff_paths(a, b, at=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append(at + "/" + key)
            else:
                out += diff_paths(a[key], b[key], at + "/" + key)
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff_paths(x, y, at + "/" + str(i))
        return out
    return [] if a == b else [at or "/"]


def standard_reasons():
    text = STANDARD.read_text()
    section = text.split("\n## Refusal reasons\n", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `([a-z_]+)` +\|", section, re.M))


def readme_rows(path):
    return set(re.findall(r"^\| `([a-z0-9_-]+)` +\|", path.read_text(), re.M))


def positive_controls():
    schemas = [json.loads((BASE / (k + ".schema.json")).read_text()) for k in KINDS]
    require(
        all(s["$defs"] == schemas[0]["$defs"] for s in schemas),
        "shared_definitions_drift",
    )
    policy_bytes = BASELINE["source-policy"].read_bytes()
    policy = strict_load(policy_bytes)
    plan_bytes = BASELINE["acquisition-plan"].read_bytes()
    plan = strict_load(plan_bytes)
    for name in ("acquisition-plan.json", "acquisition-plan-compromise.json"):
        paths = dict(BASELINE, **{"acquisition-plan": EXAMPLES / name})
        require(check_case(paths) is None, "baseline:" + name)
    for outcome in ("unavailable", "rejected", "indeterminate", "registered"):
        paths = dict(
            BASELINE,
            **{"registration-result": EXAMPLES / ("registration-" + outcome + ".json")},
        )
        require(check_case(paths) is None, "baseline:" + outcome)
    result = semantic(policy, plan, None, policy_bytes, plan_bytes)
    require(
        result == {"headroom_bps": 2000, "byte_basis": "response_body"},
        "default_projection",
    )
    require(
        plan["work_manifest"]["digest"]
        == digest((EXAMPLES / "work-manifest.json").read_bytes()),
        "work_pin_mismatch",
    )
    registered = strict_load((EXAMPLES / "registration-registered.json").read_bytes())
    require(
        registered["authority"]["profile"]["digest"]
        == digest((EXAMPLES / "authority-profile.json").read_bytes()),
        "authority_profile_pin",
    )
    # Ceiling boundary: 10 requests/s at 20% headroom admits 8/s, so a
    # 60-second allocation of exactly 480 fits; the reject vector asks for 481.
    boundary = copy.deepcopy(registered)
    boundary["allocation"]["requests"] = 480
    semantic(policy, plan, boundary, policy_bytes, plan_bytes)
    # A body-byte meter without basis projects the response_body default.
    default_policy = copy.deepcopy(policy)
    default_policy["meters"]["body_bytes"] = {
        "algorithm": "rolling_window",
        "limit": 1024,
        "window_seconds": 1,
    }
    default_policy["meter_review"]["unconfigured"] = ["errors"]
    default_plan = copy.deepcopy(plan)
    default_plan["policy"]["digest"] = digest(encoded(default_policy))
    require(shape("source-policy", default_policy), "default_meter_shape")
    require(
        semantic(default_policy, default_plan, None, encoded(default_policy), b"")
        == result,
        "explicit_meter_default_projection",
    )
    compromise_bytes = (EXAMPLES / "acquisition-plan-compromise.json").read_bytes()
    compromise_plan = strict_load(compromise_bytes)
    coverage_path = EXAMPLES / "coverage-planning-scope.json"
    coverage = strict_load(coverage_path.read_bytes())
    checked = subprocess.run(
        [
            "goneat",
            "validate",
            "data",
            "--schema-file",
            str(
                ROOT
                / "schemas/coverage-attestation/v0/coverage-attestation.schema.json"
            ),
            "--data",
            str(coverage_path),
        ],
        capture_output=True,
    )
    require(checked.returncode == 0, "coverage_shape")
    choice = compromise_plan["compromise"]
    partition = coverage["claims"][0]["scope"]["partition"]
    require(
        partition["plan_digest"] == digest(compromise_bytes), "coverage_plan_binding"
    )
    require(
        json.loads(partition["declared_scope_limit"]) == choice["declared_scope_limit"]
        and int(partition["effective_cadence_seconds"])
        == choice["effective_cadence_seconds"],
        "coverage_scope_flow",
    )
    actor = choice["chosen_by"]
    require(
        partition["chosen_by"]
        == actor["kind"] + ":" + actor["scope"] + "/" + actor["id"]
        and partition["chosen_at"] == choice["chosen_at"]
        and partition["reason"] == choice["reason"],
        "coverage_choice_flow",
    )
    require(
        coverage["coverage_state"] == "unknown"
        and coverage["protection"]["default_action"] == "block_export"
        and "volume" not in coverage["claims"][0]
        and coverage["gaps"][0]["note"] == choice["exclusions"][0],
        "coverage_overclaim",
    )
    return result


def schema_rejects():
    examples = {
        "source-policy": [EXAMPLES / "source-policy.json"],
        "acquisition-plan": sorted(EXAMPLES.glob("acquisition-plan*.json")),
        "registration-result": sorted(EXAMPLES.glob("registration-*.json")),
    }
    names = []
    for path in sorted((REJECTS / "schema").glob("reject-*.json")):
        kind, _, name = path.stem[len("reject-") :].partition("--")
        require(kind in KINDS and name, "schema_reject_name:" + path.name)
        value = strict_load(path.read_bytes())
        require(not shape_file(kind, path), "schema_reject_accepted:" + path.name)
        require(
            any(
                len(diff_paths(strict_load(e.read_bytes()), value)) == 1
                for e in examples[kind]
            ),
            "schema_reject_not_single_change:" + path.name,
        )
        names.append(path.stem[len("reject-") :])
    return names


def semantic_rejects():
    names, reasons = [], set()
    for directory in sorted((REJECTS / "semantic").glob("reject-*")):
        reason, _, name = directory.name[len("reject-") :].partition("--")
        require(reason and name, "semantic_reject_name:" + directory.name)
        present = [k for k in KINDS if (directory / (k + ".json")).exists()]
        require(
            present
            and sorted(p.name for p in directory.iterdir())
            == sorted(k + ".json" for k in present),
            "semantic_reject_contents:" + directory.name,
        )
        got = check_case(case_paths(directory))
        require(got == reason, "wrong_refusal:" + directory.name + ":" + str(got))
        names.append(directory.name[len("reject-") :])
        reasons.add(reason)
    return names, reasons


def main():
    defaults = positive_controls()
    schema = schema_rejects()
    semantic_names, reasons = semantic_rejects()
    documented = standard_reasons()
    require(
        reasons == documented,
        "reason_table_drift:undocumented="
        + ",".join(sorted(reasons - documented))
        + ":unexercised="
        + ",".join(sorted(documented - reasons)),
    )
    listed = readme_rows(REJECTS / "README.md")
    vectors = set(schema) | set(semantic_names)
    require(
        listed == vectors,
        "rejects_readme_drift:" + ",".join(sorted(listed ^ vectors)),
    )
    print(
        json.dumps(
            {
                "positive_objects": 8,
                "schema_rejects": len(schema),
                "semantic_rejects": len(semantic_names),
                "refusal_reasons": len(reasons),
                "defaults": defaults,
                "coverage_scope_flow": "checked",
                "runtime_qualification": "none",
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Refusal as error:
        print("[!!] data-acquisition controls: " + str(error), file=sys.stderr)
        sys.exit(1)
