#!/usr/bin/env python3
"""Synthetic shape/pin/semantic controls; no runtime or authority qualification.

Invocation set (PDR-0006): Python 3 stdlib and goneat JSON Schema validation.
No network requests or instance-selected executable/schema paths are used.
"""

import copy
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import tempfile
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "schemas/data-acquisition/v0"


class Refusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


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


def semantic(policy, plan, result=None, policy_bytes=None, plan_bytes=None):
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
    expected_policy = {
        "id": policy["policy_id"],
        "digest": digest(policy_bytes or encoded(policy)),
    }
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
    if result:
        require(
            result["policy"] == expected_policy
            and result["entity"] == policy["entity"]
            and result["source"] == policy["source"],
            "registration_policy_binding",
        )
        require(
            result["plan"]
            == {"id": plan["plan_id"], "digest": digest(plan_bytes or encoded(plan))},
            "registration_plan_binding",
        )
        require(instant(result["recorded_at"]) >= created, "registration_time_order")
        if result["outcome"] == "registered":
            a = result["allocation"]
            require(
                instant(a["closes_at"]) > instant(a["opens_at"]) >= start,
                "invalid_allocation_window",
            )
            require(a["requests"] > 0, "zero_allocation")
            require(
                all(name in a for name in ("body_bytes", "errors") if name in meters),
                "allocation_missing_meter",
            )
    return {
        "headroom_bps": policy.get("headroom_bps", 2000),
        "byte_basis": meters.get("body_bytes", {}).get("basis", "response_body"),
    }


def shape(kind, value):
    with tempfile.TemporaryDirectory(prefix="acquisition-control-") as tmp:
        path = pathlib.Path(tmp) / "instance.json"
        path.write_bytes(encoded(value))
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


def main():
    examples = BASE / "examples"
    policy = json.loads((examples / "source-policy.json").read_text())
    plan = json.loads((examples / "acquisition-plan.json").read_text())
    schemas = [
        json.loads((BASE / (n + ".schema.json")).read_text())
        for n in ("source-policy", "acquisition-plan", "registration-result")
    ]
    require(
        all(s["$defs"] == schemas[0]["$defs"] for s in schemas),
        "shared_definitions_drift",
    )
    require(
        shape("source-policy", policy) and shape("acquisition-plan", plan),
        "baseline_shape",
    )
    result = semantic(
        policy, plan, policy_bytes=(examples / "source-policy.json").read_bytes()
    )
    require(
        result == {"headroom_bps": 2000, "byte_basis": "response_body"},
        "default_projection",
    )
    require(
        plan["work_manifest"]["digest"]
        == digest((examples / "work-manifest.json").read_bytes()),
        "work_pin_mismatch",
    )
    receipts = {}
    for outcome in ("unavailable", "rejected", "indeterminate", "registered"):
        r = json.loads((examples / ("registration-" + outcome + ".json")).read_text())
        require(shape("registration-result", r), "receipt_shape")
        semantic(
            policy,
            plan,
            r,
            (examples / "source-policy.json").read_bytes(),
            (examples / "acquisition-plan.json").read_bytes(),
        )
        if outcome == "registered":
            require(
                r["authority"]["profile"]["digest"]
                == digest((examples / "authority-profile.json").read_bytes()),
                "authority_profile_pin",
            )
        receipts[outcome] = r
    compromise_plan = json.loads(
        (examples / "acquisition-plan-compromise.json").read_text()
    )
    require(shape("acquisition-plan", compromise_plan), "compromise_shape")
    semantic(
        policy,
        compromise_plan,
        policy_bytes=(examples / "source-policy.json").read_bytes(),
    )
    coverage_path = examples / "coverage-planning-scope.json"
    coverage = json.loads(coverage_path.read_text())
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
        partition["plan_digest"]
        == digest((examples / "acquisition-plan-compromise.json").read_bytes()),
        "coverage_plan_binding",
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
        semantic(default_policy, default_plan) == result,
        "explicit_meter_default_projection",
    )
    tests = []

    def control(name, stage, reason, owner, mutate, receipt="unavailable", rebind=True):
        p, q, r = (
            copy.deepcopy(policy),
            copy.deepcopy(plan),
            copy.deepcopy(receipts[receipt]),
        )
        mutate({"policy": p, "plan": q, "result": r}[owner])
        if rebind:
            q["policy"] = {"id": p["policy_id"], "digest": digest(encoded(p))}
            r["policy"] = copy.deepcopy(q["policy"])
            r["plan"] = {"id": q["plan_id"], "digest": digest(encoded(q))}
        shaped = (
            shape("source-policy", p)
            and shape("acquisition-plan", q)
            and shape("registration-result", r)
        )
        if stage == "shape":
            require(not shaped, "shape_reject_accepted:" + name)
        else:
            require(shaped, "semantic_case_not_schema_valid:" + name)
            try:
                semantic(
                    p,
                    q,
                    r,
                    None if rebind else (examples / "source-policy.json").read_bytes(),
                    None
                    if rebind
                    else (examples / "acquisition-plan.json").read_bytes(),
                )
            except Refusal as error:
                require(
                    str(error) == reason, "wrong_refusal:" + name + ":" + str(error)
                )
            else:
                raise Refusal("semantic_reject_accepted:" + name)
        tests.append(name)

    control(
        "inline-credential",
        "shape",
        "",
        "policy",
        lambda p: p["transport"]["credential_ref"].update(value="synthetic-forbidden"),
    )
    control(
        "missing-paging",
        "shape",
        "",
        "policy",
        lambda p: p["target_set"]["targets"][0].pop("paging"),
    )
    control(
        "execution-claim",
        "shape",
        "",
        "plan",
        lambda p: p.update(execution_authorization="granted"),
    )
    control(
        "unknown-budget-algorithm",
        "shape",
        "",
        "policy",
        lambda p: p["meters"]["requests"].update(algorithm="token_bucket"),
    )
    control(
        "unavailable-allocation",
        "shape",
        "",
        "result",
        lambda r: r.update(allocation=receipts["registered"]["allocation"]),
    )
    control(
        "indeterminate-without-key",
        "shape",
        "",
        "result",
        lambda r: r.pop("reconcile_key"),
        receipt="indeterminate",
    )
    control(
        "terms-changed",
        "semantic",
        "terms_changed",
        "policy",
        lambda p: p["access_terms"].update(current_digest="sha256:" + "b" * 64),
    )
    control(
        "review-after-start",
        "semantic",
        "review_after_start",
        "policy",
        lambda p: p["access_terms"].update(reviewed_at="2026-01-03T00:00:00Z"),
    )
    control(
        "meter-absence",
        "semantic",
        "unreviewed_meter_absence",
        "policy",
        lambda p: p["meter_review"].update(unconfigured=[]),
    )
    control(
        "zero-request-meter",
        "semantic",
        "zero_meter",
        "policy",
        lambda p: p["meters"]["requests"].update(limit=0),
    )
    control(
        "burst-over-window",
        "semantic",
        "burst_exceeds_window",
        "policy",
        lambda p: p["meters"]["requests"].update(burst=11),
    )
    control(
        "zero-concurrency",
        "semantic",
        "zero_concurrency",
        "policy",
        lambda p: p["transport"].update(concurrency_limit=0),
    )
    control(
        "inline-url-key",
        "semantic",
        "unsafe_target_url",
        "policy",
        lambda p: p["target_set"]["targets"][0].update(
            endpoint_uri="https://example.invalid/data?key=synthetic"
        ),
    )
    control(
        "variant-outside-vocabulary",
        "semantic",
        "variant_outside_vocabulary",
        "policy",
        lambda p: p["target_set"]["targets"][0]["variants"].update(format="csv"),
    )
    control(
        "undeclared-target",
        "semantic",
        "undeclared_target",
        "plan",
        lambda p: p["effective_scope"].update(target_ids=["missing"]),
    )
    control(
        "changed-scope-without-choice",
        "semantic",
        "compromise_required_or_spurious",
        "plan",
        lambda p: p["effective_scope"].update(time_scope="different"),
    )
    control(
        "deletion-window",
        "semantic",
        "cadence_reaches_deletion",
        "policy",
        lambda p: p.update(deletion_window_seconds=86400),
    )
    control(
        "policy-pin",
        "semantic",
        "policy_pin_mismatch",
        "plan",
        lambda p: p["policy"].update(digest="sha256:" + "0" * 64),
        rebind=False,
    )
    control(
        "receipt-source",
        "semantic",
        "registration_policy_binding",
        "result",
        lambda r: r.update(source="different"),
    )
    control(
        "receipt-plan-pin",
        "semantic",
        "registration_plan_binding",
        "result",
        lambda r: r["plan"].update(digest="sha256:" + "0" * 64),
        rebind=False,
    )
    control(
        "allocation-window",
        "semantic",
        "invalid_allocation_window",
        "result",
        lambda r: r["allocation"].update(closes_at=r["allocation"]["opens_at"]),
        receipt="registered",
    )
    control(
        "zero-allocation",
        "semantic",
        "zero_allocation",
        "result",
        lambda r: r["allocation"].update(requests=0),
        receipt="registered",
    )
    # Shape-valid byte meter controls rebind the dependent pins so the intended
    # semantic rule, not a stale fixture digest, is exercised.
    for basis, limit, reason in [
        ("response_body", 0, "zero_meter"),
        ("transfer", 10, "unsupported_meter_basis"),
    ]:

        def add_meter(p, basis=basis, limit=limit):
            p["meters"]["body_bytes"] = {
                "algorithm": "rolling_window",
                "limit": limit,
                "window_seconds": 1,
                "basis": basis,
            }
            p["meter_review"]["unconfigured"] = ["errors"]

        control("byte-meter-" + basis, "semantic", reason, "policy", add_meter)
    # Attribute/limit requirements are also exercised on a real scope choice.
    for field in ("chosen_by", "declared_scope_limit"):
        q = copy.deepcopy(compromise_plan)
        q["compromise"].pop(field)
        require(not shape("acquisition-plan", q), "missing_choice_field_accepted")
        tests.append("missing-" + field)
    q = copy.deepcopy(compromise_plan)
    q["compromise"]["effective_cadence_seconds"] = 86400
    require(shape("acquisition-plan", q), "choice_limit_shape")
    try:
        semantic(policy, q, policy_bytes=(examples / "source-policy.json").read_bytes())
    except Refusal as error:
        require(str(error) == "scope_limit_mismatch", "choice_limit_reason")
    else:
        raise Refusal("choice_limit_accepted")
    tests.append("scope-limit-mismatch")
    print(
        json.dumps(
            {
                "positive_objects": 8,
                "negative_controls": len(tests),
                "defaults": result,
                "coverage_scope_flow": "checked",
                "controls": tests,
                "runtime_qualification": "none",
            }
        )
    )


if __name__ == "__main__":
    main()
