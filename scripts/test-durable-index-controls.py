#!/usr/bin/env python3
"""Initial design controls, not a physical reader or publication qualifier.

Python stdlib plus goneat (JSON Schema subject matter) is the closed invocation
set. Inputs are repository-owned files. Logical vectors use normalized evidence;
this checker does not validate a production coverage graph or Parquet bytes.
"""

import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "schemas/durable-index/v0"
SCHEMAS = ROOT / "schemas"


class Refusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_key")
            result[key] = value
        return result

    def invalid(_):
        raise Refusal("invalid_json")

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)

    def scalar(item):
        if isinstance(item, str):
            try:
                item.encode("utf-8")
            except UnicodeError:
                raise Refusal("invalid_unicode") from None
        elif isinstance(item, dict):
            for key, child in item.items():
                scalar(key)
                scalar(child)
        elif isinstance(item, list):
            for child in item:
                scalar(child)

    scalar(value)
    return value


def instant(value):
    require(
        isinstance(value, str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{9}Z", value),
        "invalid_instant",
    )
    try:
        datetime.datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        raise Refusal("invalid_instant") from None
    return value  # fixed-width UTC text preserves all nanoseconds in comparisons


def key(row):
    return row["namespace"].encode(), row["key"].encode()


def scope_key(scope):
    return scope["namespace"].encode(), scope["prefix"].encode()


def contains(scope, namespace, value):
    return scope["namespace"] == namespace and value.startswith(scope["prefix"])


def canonical(scopes):
    require(len(scopes) <= 65536, "capacity")
    unique = sorted({scope_key(scope) for scope in scopes})
    require(all(len(prefix) <= 4096 for _, prefix in unique), "capacity")
    result = []
    for namespace, prefix in unique:
        if not any(ns == namespace and prefix.startswith(p) for ns, p in result):
            result.append((namespace, prefix))
    return [{"namespace": ns.decode(), "prefix": p.decode()} for ns, p in result]


def plan_bytes(set_id, scopes):
    scopes = canonical(scopes)

    def frame(value):
        raw = value.encode()
        return len(raw).to_bytes(4, "big") + raw

    raw = b"durable-index/v0/plan\x00" + frame(set_id)
    raw += len(scopes).to_bytes(4, "big")
    for scope in scopes:
        raw += frame(scope["namespace"]) + frame(scope["prefix"])
    return raw


def digest(set_id, scopes):
    return hashlib.sha256(plan_bytes(set_id, scopes)).hexdigest()


def loss(old, new):
    return any(
        not any(contains(b, a["namespace"], a["prefix"]) for b in new)
        for a in canonical(old)
    )


def fold(case):
    """Small logical model over authored, normalized inputs; no storage IO."""
    mode, parent = case["mode"], case["parent"]
    require(case["discovery_complete"], "discovery_failed")
    scopes = case["scopes"]
    require(scopes == canonical(scopes), "noncanonical_plan")
    if mode == "baseline":
        require(parent is None and case["generation"] == 0, "invalid_baseline")
        require(case["acknowledgment"] is None, "unexpected_acknowledgment")
        rows, admission = {}, "baseline_not_compared"
    else:
        require(parent is not None, "parent_unavailable")
        require(parent["set_id"] == case["set_id"], "set_mismatch")
        require(parent["snapshot_id"] != case["snapshot_id"], "snapshot_reuse")
        require(parent["generation"] + 1 == case["generation"], "generation_mismatch")
        require(
            parent["publication_sha256"] == case["admitted_parent_sha256"],
            "stale_parent",
        )
        rows = {key(row): copy.deepcopy(row) for row in parent["rows"]}
        require(len(rows) == len(parent["rows"]), "duplicate_key_row")
        if mode == "enrich":
            require(scopes == parent["scopes"], "enrichment_scope_change")
            require(not case["observations"], "enrichment_observation")
            require(case["observation_at"] is None, "enrichment_observation")
            require(case["acknowledgment"] is None, "unexpected_acknowledgment")
            admission = "inherited"
        elif loss(parent["scopes"], scopes):
            ack = case["acknowledgment"]
            require(ack is not None, "scope_loss")
            require(
                ack["parent_sha256"] == parent["publication_sha256"]
                and ack["plan_digest"] == digest(case["set_id"], scopes),
                "acknowledgment_mismatch",
            )
            admission = "loss_acknowledged"
        else:
            require(case["acknowledgment"] is None, "unexpected_acknowledgment")
            admission = "no_loss"
    stamp = {"snapshot_id": case["snapshot_id"], "at": case["observation_at"]}
    if mode != "enrich":
        instant(stamp["at"])
        for old in rows.values():
            require(
                max(old["last_seen"]["at"], old["last_changed"]["at"]) <= stamp["at"],
                "clock_reversal",
            )
        observed = set()
        fields = ("revision", "size_bytes", "last_modified", "storage_class")
        for obs in case["observations"]:
            k = key(obs)
            require(k not in observed, "duplicate_observation")
            observed.add(k)
            require(
                any(contains(s, obs["namespace"], obs["key"]) for s in scopes),
                "observation_outside_plan",
            )
            old = rows.get(k)
            if old is None:
                row = {
                    **copy.deepcopy(obs),
                    "first_seen": stamp,
                    "last_seen": stamp,
                    "last_changed": stamp,
                    "deleted": None,
                    "enrichments": [],
                }
            else:
                row = copy.deepcopy(old)
                if old["deleted"] is not None or any(old[f] != obs[f] for f in fields):
                    row["last_changed"] = stamp
                if obs["revision"] is None or obs["revision"] != old["revision"]:
                    row["enrichments"] = []
                row.update(copy.deepcopy(obs))
                row["last_seen"], row["deleted"] = stamp, None
            rows[k] = row
        # These scopes are normalized, already-verified I3 evidence in this
        # logical corpus, NOT arbitrary producer assertions of completeness.
        for scope in case["absence_authority"]:
            require(scope in scopes, "coverage_outside_plan")
        for k, row in rows.items():
            if (
                k not in observed
                and row["deleted"] is None
                and any(
                    contains(s, row["namespace"], row["key"])
                    for s in case["absence_authority"]
                )
            ):
                row["deleted"] = stamp
                row["last_changed"] = stamp
                row["enrichments"] = []
    else:
        require(not case["absence_authority"], "enrichment_observation")
    seen_attributes = set()
    for update in case["enrichments"]:
        row = rows.get(key(update))
        require(row is not None and row["deleted"] is None, "enrichment_target")
        attribute = update["attribute"]
        identity = key(update), attribute["name"]
        require(identity not in seen_attributes, "duplicate_enrichment")
        seen_attributes.add(identity)
        require(
            row["revision"] is not None
            and attribute["against_revision"] == row["revision"],
            "enrichment_revision",
        )
        instant(attribute["observed_at"])
        attributes = {item["name"]: item for item in row["enrichments"]}
        old = attributes.get(attribute["name"])
        require(
            old is None or old["observed_at"] <= attribute["observed_at"],
            "stale_enrichment",
        )
        attributes[attribute["name"]] = copy.deepcopy(attribute)
        row["enrichments"] = [attributes[name] for name in sorted(attributes)]
    output = [rows[k] for k in sorted(rows)]
    return {
        "rows": output,
        "admission": admission,
        "retained_unobserved_rows": sum(
            row["last_seen"]["snapshot_id"] != case["snapshot_id"] for row in output
        ),
    }


def shape(path, schema):
    result = subprocess.run(
        [
            "goneat",
            "validate",
            "data",
            "--schema-file",
            str(schema),
            "--ref-dir",
            str(BASE),
            "--ref-dir",
            str(SCHEMAS / "segmented-snapshot/v0"),
            "--data",
            str(path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    try:
        report, end = json.JSONDecoder().raw_decode(result.stderr.lstrip())
        assert result.returncode == 1 and report["valid"] is False and report["errors"]
        assert (
            result.stderr.lstrip()[end:]
            .lstrip()
            .startswith("Error: data validation failed")
        )
        return False
    except (ValueError, KeyError, AssertionError):
        raise RuntimeError(
            "validator execution failed: " + result.stdout + result.stderr
        ) from None


def main():
    inventory = strict((BASE / "cases.json").read_bytes())
    actual = {
        str(p.relative_to(BASE))
        for folder in ("examples", "rejects", "vectors")
        for p in (BASE / folder).rglob("*.json")
    }
    listed = {entry["file"] for entry in inventory["shape"]}
    listed.update(inventory["plans"] + inventory["transitions"])
    require(listed == actual, "fixture_inventory")
    for entry in inventory["shape"]:
        if not entry["valid"]:
            kind = Path(entry["file"]).name.split("--")[0].removeprefix("reject-")
            original = strict((BASE / "examples" / f"{kind}.json").read_bytes())
            rejected = strict((BASE / entry["file"]).read_bytes())
            missing = object()
            changed = [
                k
                for k in original.keys() | rejected.keys()
                if original.get(k, missing) != rejected.get(k, missing)
            ]
            assert len(changed) == 1, (entry["file"], changed)
        assert shape(BASE / entry["file"], BASE / entry["schema"]) == entry["valid"], (
            entry
        )
    metadata = strict((BASE / "examples/index-metadata.json").read_bytes())
    example_bindings = [(metadata["plan"], "index-plan.json")]
    example_bindings += [
        (pin, f"coverage-{i}.json") for i, pin in enumerate(metadata["coverage"])
    ]
    for pin, filename in example_bindings:
        raw = (BASE / "examples" / filename).read_bytes()
        assert pin["byte_length"] == len(raw)
        assert pin["sha256"] == hashlib.sha256(raw).hexdigest()
    for filename in inventory["plans"]:
        case = strict((BASE / filename).read_bytes())
        assert canonical(case["input"]) == case["canonical"], filename
        assert plan_bytes(case["set_id"], case["input"]).hex() == case["bytes_hex"], (
            filename
        )
        assert digest(case["set_id"], case["input"]) == case["sha256"], filename
        for member in case.get("membership", []):
            assert (
                contains(member["scope"], member["namespace"], member["key"])
                == member["contains"]
            ), filename
        for comparison in case["comparisons"]:
            assert loss(case["canonical"], comparison["next"]) == comparison["loss"], (
                filename
            )
    with tempfile.TemporaryDirectory(prefix="durable-index-controls-") as tmp:
        path = Path(tmp) / "row.json"
        for filename in inventory["transitions"]:
            case = strict((BASE / filename).read_bytes())
            outcome = None
            try:
                outcome = fold(case["input"])
            except Refusal as error:
                outcome = {"refusal": str(error)}
            assert outcome == case["expected"], (filename, outcome, case["expected"])
            for row in outcome.get("rows", []):
                path.write_text(json.dumps(row))
                assert shape(path, BASE / "index-row.schema.json"), filename
            print(f"[ok] {filename}")
    for raw, reason in [
        (b'{"a":1,"a":2}', "duplicate_key"),
        (b'{"a":NaN}', "invalid_json"),
        (b'{"a":"\\ud800"}', "invalid_unicode"),
    ]:
        try:
            strict(raw)
        except Refusal as error:
            assert str(error) == reason
        else:
            raise AssertionError(reason)
    print(
        f"Durable index DESIGN controls PASS: {len(inventory['shape'])} shapes, "
        f"{len(inventory['plans'])} plan vectors, {len(inventory['transitions'])} transitions. "
        "No Parquet, coverage-graph or runtime qualification claim."
    )


if __name__ == "__main__":
    main()
