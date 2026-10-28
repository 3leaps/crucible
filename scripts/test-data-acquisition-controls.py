#!/usr/bin/env python3
"""Synthetic shape/pin/semantic controls; no runtime or authority qualification.

Invocation set (PDR-0006): Python 3 stdlib and goneat JSON Schema validation.
No network requests or instance-selected executable/schema paths are used.

Fixtures on disk are the vectors. Schema rejects live in rejects/schema/ as
reject-<object>--<name>.json. Semantic rejects live in rejects/semantic/ as
reject-<reason>--<name>/ directories holding only the objects that differ from
the baseline; an absent object is the corresponding file in examples/. Ledger
rejects live in rejects/ledger/ as reject-<reason>--<name>/ledger.json: an
ordered list of registration results checked as one authority's record.
Vectors whose outcome depends on this checker's profile carry a
checker-profile.json label.
"""

import copy
import datetime as dt
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "schemas/data-acquisition/v0"
EXAMPLES = BASE / "examples"
REJECTS = BASE / "rejects"
STANDARD = ROOT / "docs/standards/data-acquisition-contract.md"
KINDS = ("source-policy", "acquisition-plan", "registration-result")
_tspec = importlib.util.spec_from_file_location(
    "rfc3339", ROOT / "scripts/rfc3339-instant.py"
)
_rfc3339 = importlib.util.module_from_spec(_tspec)
_tspec.loader.exec_module(_rfc3339)
_FRACTION = re.compile(r"[Tt]\d{2}:\d{2}:\d{2}\.(\d+)")
# This checker's profile: exact instants to the microsecond, response-body
# byte meters only. Vectors that depend on it are labelled.
PROFILE = {"timestamp_resolution": "microsecond", "byte_basis": ["response_body"]}
PROFILE_REASONS = {
    "unrepresentable_precision": "timestamp_resolution",
    "unsupported_meter_basis": "byte_basis",
}
PLANS = (
    EXAMPLES / "acquisition-plan.json",
    EXAMPLES / "acquisition-plan-compromise.json",
)
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
    """Exact UTC instant. This checker resolves microseconds and refuses any
    finer non-zero fraction rather than truncating it."""
    require(isinstance(value, str) and value.endswith("Z"), "utc_required")
    m = _FRACTION.search(value)
    require(
        not (m and len(m.group(1)) > 6 and m.group(1)[6:].strip("0")),
        "unrepresentable_precision",
    )
    try:
        return _rfc3339.parse_rfc3339(value)
    except ValueError:
        raise Refusal("invalid_time")


def invisible(c):
    """Whitespace, C0/C1 control or format character: never part of a v0 URL."""
    return c.isspace() or unicodedata.category(c) in ("Cc", "Cf")


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


def semantic(
    policy, plan, result, policy_bytes, plan_bytes, byte_basis=PROFILE["byte_basis"]
):
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
        meters.get("body_bytes", {}).get("basis", "response_body") in byte_basis,
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
        raw_url = target["endpoint_uri"]
        # An empty query or fragment still carries its delimiter; refuse the
        # delimiter itself, and any invisible character.
        require(
            "?" not in raw_url
            and "#" not in raw_url
            and not any(invisible(c) for c in raw_url),
            "unsafe_target_url",
        )
        try:
            u = urlsplit(raw_url)
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
        require(set(target["variants"]) == set(dimensions), "missing_variant")
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
            # One allocation alone must fit the parent ceiling. Allocation
            # sets are checked by ledger(); the authority checks its full record.
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


def ledger(policy, policy_bytes, plans, results):
    """Check an ordered record of registration results under one policy.

    plans maps a plan pin digest to (plan, plan_bytes). Each result must pass
    semantic() alone; the record must then agree on request identity and
    replay, and its distinct allocations must fit every span they occupy.
    """
    for r in results:
        found = plans.get(r["plan"]["digest"])
        require(
            found and found[0]["plan_id"] == r["plan"]["id"],
            "registration_plan_binding",
        )
        semantic(policy, found[0], r, policy_bytes, found[1])
    keys, requests = {}, {}
    for r in results:
        keys.setdefault(r["idempotency_key"], set()).add(r["request_id"])
        requests.setdefault(r["request_id"], set()).add(r["idempotency_key"])
    require(
        all(len(v) == 1 for v in keys.values())
        and all(len(v) == 1 for v in requests.values()),
        "request_identity_mismatch",
    )
    originals = {}
    for r in results:
        proposal = (r["request_id"], r["policy"], r["plan"])
        first = originals.setdefault(r["idempotency_key"], {"proposal": proposal})
        require(first["proposal"] == proposal, "replay_mismatch")
        # After a final result, every later entry for the key must be exactly
        # that result; a non-final outcome there is not a conforming replay.
        if "result" in first:
            require(r == first["result"], "replay_mismatch")
        elif r["outcome"] in ("rejected", "registered"):
            first["result"] = r
    registered = [
        o["result"]
        for o in originals.values()
        if o.get("result", {}).get("outcome") == "registered"
    ]
    ids = [r["allocation"]["id"] for r in registered]
    require(len(ids) == len(set(ids)), "duplicate_allocation")
    meters = policy["meters"]
    headroom = policy.get("headroom_bps", 2000)
    spans = [
        (instant(r["allocation"]["opens_at"]), instant(r["allocation"]["closes_at"]), r)
        for r in registered
    ]
    # Intervals are half-open. Allocations wholly inside a span share every
    # rolling window that covers it, so their sum must fit its ceiling.
    for start in {s for s, _, _ in spans}:
        for end in {e for _, e, _ in spans}:
            if end <= start:
                continue
            inside = [r["allocation"] for s, e, r in spans if s >= start and e <= end]
            for name in meters:
                require(
                    sum(a[name] for a in inside)
                    <= ceiling(meters[name], headroom, end - start),
                    "allocations_exceed_policy",
                )
    return len(registered)


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
        encoding="utf-8",
        errors="replace",
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
    # An interval just over 60 windows spans 61, so 61 * 8 requests fit.
    boundary["allocation"]["closes_at"] = "2026-01-02T00:01:00.000001Z"
    boundary["allocation"]["requests"] = 488
    semantic(policy, plan, boundary, policy_bytes, plan_bytes)
    # Exact instants: equal creation and start, and a microsecond fraction
    # with zero padding beyond six digits, are both accepted.
    same = copy.deepcopy(plan)
    same["created_at"] = same["start_at"] = "2026-01-02T00:00:00.000001000Z"
    semantic(policy, same, None, policy_bytes, encoded(same))
    # The parser accepts a lowercase t separator; the precision guard must too.
    require(
        instant("2026-01-02t00:00:00.000001000Z") == instant(same["start_at"]),
        "lowercase_t_zero_padding",
    )
    # Percent-escaped delimiters are ordinary path content, and non-ASCII
    # letters are not invisible; both stay acceptable.
    escaped = copy.deepcopy(policy)
    escaped["target_set"]["targets"][0]["endpoint_uri"] = (
        "https://example.invalid/obs%3Fkey%23frag/caf\u00e9"
    )
    escaped_plan = copy.deepcopy(plan)
    escaped_plan["policy"]["digest"] = digest(encoded(escaped))
    require(shape("source-policy", escaped), "escaped_path_shape")
    semantic(escaped, escaped_plan, None, encoded(escaped), encoded(escaped_plan))
    # Target bounds: a policy catalog holds at most 4096 targets and one plan
    # scope selects at most 256; neither bound splits or widens the other.
    wide = copy.deepcopy(policy)
    template = wide["target_set"]["targets"][0]
    wide["target_set"]["targets"] = [
        dict(copy.deepcopy(template), id="t%04d" % i) for i in range(4096)
    ]
    require(shape("source-policy", wide), "policy_target_bound_accepted")
    wide_bytes = encoded(wide)
    selected = copy.deepcopy(plan)
    selected["policy"]["digest"] = digest(wide_bytes)
    ids = ["t%04d" % i for i in range(256)]
    selected["original_scope"]["target_ids"] = ids
    selected["effective_scope"]["target_ids"] = list(ids)
    require(shape("acquisition-plan", selected), "plan_target_bound_accepted")
    semantic(wide, selected, None, wide_bytes, encoded(selected))
    wide["target_set"]["targets"].append(dict(copy.deepcopy(template), id="t4096"))
    require(not shape("source-policy", wide), "policy_target_bound_exceeded")
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


def profile_label(directory, reason, documented):
    """Validate checker-profile.json; required exactly for profile reasons."""
    label = directory / "checker-profile.json"
    require(
        label.exists() == (reason in PROFILE_REASONS),
        "checker_profile_label:" + directory.name,
    )
    if not label.exists():
        return
    value = strict_load(label.read_bytes())
    require(
        set(value) == {"checker_profile", "reason_outside_profile"}
        and value["checker_profile"]
        == {PROFILE_REASONS[reason]: PROFILE[PROFILE_REASONS[reason]]}
        and (
            value["reason_outside_profile"] is None
            or value["reason_outside_profile"] in documented
        ),
        "checker_profile_label:" + directory.name,
    )
    if reason == "unsupported_meter_basis":
        # Verifiable here: a consumer qualifying both bases gives the label's outcome.
        paths = case_paths(directory)
        raw = {k: p.read_bytes() for k, p in paths.items()}
        objects = {k: strict_load(b) for k, b in raw.items()}
        try:
            semantic(
                objects["source-policy"],
                objects["acquisition-plan"],
                objects.get("registration-result"),
                raw["source-policy"],
                raw["acquisition-plan"],
                byte_basis=("response_body", "transfer"),
            )
            got = None
        except Refusal as error:
            got = str(error)
        require(
            got == value["reason_outside_profile"],
            "checker_profile_outcome:" + directory.name,
        )


def semantic_rejects(documented):
    names, reasons = [], set()
    for directory in sorted((REJECTS / "semantic").glob("reject-*")):
        reason, _, name = directory.name[len("reject-") :].partition("--")
        require(reason and name, "semantic_reject_name:" + directory.name)
        present = [k for k in KINDS if (directory / (k + ".json")).exists()]
        extra = ["checker-profile.json"] if reason in PROFILE_REASONS else []
        require(
            present
            and sorted(p.name for p in directory.iterdir())
            == sorted([k + ".json" for k in present] + extra),
            "semantic_reject_contents:" + directory.name,
        )
        profile_label(directory, reason, documented)
        got = check_case(case_paths(directory))
        require(got == reason, "wrong_refusal:" + directory.name + ":" + str(got))
        names.append(directory.name[len("reject-") :])
        reasons.add(reason)
    return names, reasons


def load_plans():
    plans = {}
    for path in PLANS:
        raw = path.read_bytes()
        plans[digest(raw)] = (strict_load(raw), raw)
    return plans


def check_ledger(path):
    policy_bytes = BASELINE["source-policy"].read_bytes()
    try:
        results = strict_load(path.read_bytes())
        require(isinstance(results, list) and results, "ledger_shape")
        for r in results:
            if not shape("registration-result", r):
                return "shape:registration-result"
        ledger(strict_load(policy_bytes), policy_bytes, load_plans(), results)
    except Refusal as error:
        return str(error)
    return None


def ledger_rejects():
    names, reasons = [], set()
    for directory in sorted((REJECTS / "ledger").glob("reject-*")):
        reason, _, name = directory.name[len("reject-") :].partition("--")
        require(reason and name, "ledger_reject_name:" + directory.name)
        require(
            [p.name for p in directory.iterdir()] == ["ledger.json"],
            "ledger_reject_contents:" + directory.name,
        )
        got = check_ledger(directory / "ledger.json")
        require(got == reason, "wrong_refusal:" + directory.name + ":" + str(got))
        names.append(directory.name[len("reject-") :])
        reasons.add(reason)
    return names, reasons


def multiple_fault_rejects(documented):
    """Inputs breaking several rules: any listed applicable reason is accepted."""
    names = []
    for directory in sorted((REJECTS / "multiple").glob("reject-*")):
        expect = directory / "applicable-reasons.json"
        allowed = strict_load(expect.read_bytes())
        require(
            len(allowed) >= 2 and set(allowed) <= documented,
            "multiple_reject_reasons:" + directory.name,
        )
        present = [k for k in KINDS if (directory / (k + ".json")).exists()]
        require(
            present
            and sorted(p.name for p in directory.iterdir())
            == sorted([k + ".json" for k in present] + [expect.name]),
            "multiple_reject_contents:" + directory.name,
        )
        got = check_case(case_paths(directory))
        require(got in allowed, "wrong_refusal:" + directory.name + ":" + str(got))
        names.append(directory.name[len("reject-") :])
    return names


def main():
    defaults = positive_controls()
    require(
        check_ledger(EXAMPLES / "allocation-ledger.json") is None, "baseline:ledger"
    )
    schema = schema_rejects()
    documented = standard_reasons()
    semantic_names, reasons = semantic_rejects(documented)
    ledger_names, ledger_reasons = ledger_rejects()
    reasons |= ledger_reasons
    require(
        reasons == documented,
        "reason_table_drift:undocumented="
        + ",".join(sorted(reasons - documented))
        + ":unexercised="
        + ",".join(sorted(documented - reasons)),
    )
    multiple = multiple_fault_rejects(documented)
    listed = readme_rows(REJECTS / "README.md")
    vectors = set(schema) | set(semantic_names) | set(multiple) | set(ledger_names)
    require(
        listed == vectors,
        "rejects_readme_drift:" + ",".join(sorted(listed ^ vectors)),
    )
    print(
        json.dumps(
            {
                "positive_objects": 9,
                "schema_rejects": len(schema),
                "semantic_rejects": len(semantic_names),
                "multiple_fault_rejects": len(multiple),
                "ledger_rejects": len(ledger_names),
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
