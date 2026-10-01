#!/usr/bin/env python3
"""Repository-only structural/semantic controls for segmented-snapshot/v0.

The resolver is an in-memory map of committed synthetic fixture bytes, never a
network client or a production storage reader. Runtime custody, crash durability,
authorization and retention still require adopter evidence.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import pathlib
import subprocess
import tempfile
import urllib.parse
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parent.parent
FAMILY = REPO / "schemas/segmented-snapshot/v0"
BASE = FAMILY / "fixtures/base"
CAPABILITY = "contract: segmented-snapshot/v0"
SAFE_INTEGER = 9007199254740991
FILES = {
    "artifact:profile-spec": "profile-spec.md",
    "artifact:retention-spec": "retention-spec.md",
    "artifact:profile": "profile.json",
    "artifact:row-schema": "rows.schema.json",
    "artifact:catalog": "catalog.json",
    "artifact:descriptor": "descriptor.json",
    "artifact:member-a": "member-a.ndjson",
    "artifact:member-b": "member-b.ndjson",
    "artifact:manifest": "manifest.json",
    "artifact:publication": "publication.json",
    "artifact:coverage": "coverage.json",
    "artifact:result": "result.json",
}
SCHEMAS = {
    "artifact:profile": FAMILY / "snapshot-profile.schema.json",
    "artifact:manifest": FAMILY / "snapshot-manifest.schema.json",
    "artifact:publication": FAMILY / "snapshot-publication.schema.json",
    "artifact:result": FAMILY / "verification-result.schema.json",
    "artifact:descriptor": REPO
    / "schemas/data-artifact/v0/artifact-descriptor.schema.json",
    "artifact:catalog": REPO
    / "schemas/data-artifact/v0/artifact-descriptor.schema.json#/$defs/fieldCatalog",
    "artifact:coverage": REPO
    / "schemas/coverage-attestation/v0/coverage-attestation.schema.json",
}


class Violation(Exception):
    pass


def require(condition: bool, rule: str) -> None:
    if not condition:
        raise Violation(rule)


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "SEM-S00")
        result[key] = value
    return result


def parse(raw: bytes) -> dict:
    return json.loads(raw, object_pairs_hook=unique_object)


def emitted(value: object) -> bytes:
    """Fixture emission only; never used to verify a physical byte digest."""
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def binding(raw: bytes, ref: str, identity: str) -> dict:
    return {
        "id": identity,
        "ref": ref,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_length": len(raw),
    }


def subject_uri(selection: dict) -> str:
    data = b"segmented-snapshot/v0/subject\x00"
    data += selection["namespace_id"].encode("ascii") + b"\x00"
    data += selection["snapshot_id"].encode("ascii")
    return "snapshot:" + hashlib.sha256(data).hexdigest()


@functools.lru_cache(maxsize=128)
def check_row_schema(raw: bytes) -> None:
    """Check the first wire version's static, local Draft 2020-12 schema graph."""
    root = parse(raw)
    require(
        root.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "SEM-S03"
    )
    single = {
        "additionalProperties",
        "unevaluatedProperties",
        "propertyNames",
        "contains",
        "items",
        "not",
        "if",
        "then",
        "else",
        "unevaluatedItems",
        "contentSchema",
    }
    arrays = {"allOf", "anyOf", "oneOf", "prefixItems"}
    maps = {"properties", "patternProperties", "dependentSchemas", "$defs"}
    nodes, anchors, references = {}, {}, []

    def visit(value: object, path: tuple) -> None:
        require(isinstance(value, (dict, bool)), "SEM-S03")
        nodes[path] = value
        if isinstance(value, bool):
            return
        require(not path or "$id" not in value, "SEM-S03")
        require(
            "$schema" not in value or value["$schema"] == root["$schema"], "SEM-S03"
        )
        require(
            not {
                "$dynamicRef",
                "$dynamicAnchor",
                "$recursiveRef",
                "$recursiveAnchor",
            }.intersection(value),
            "SEM-S03",
        )
        if "$anchor" in value:
            require(value["$anchor"] not in anchors, "SEM-S03")
            anchors[value["$anchor"]] = path
        if "$ref" in value:
            require(
                isinstance(value["$ref"], str) and value["$ref"].startswith("#"),
                "SEM-S03",
            )
            references.append(value["$ref"])
        for key, item in value.items():
            if key in single:
                visit(item, path + (key,))
            elif key in arrays:
                require(isinstance(item, list), "SEM-S03")
                for i, child in enumerate(item):
                    visit(child, path + (key, str(i)))
            elif key in maps:
                require(isinstance(item, dict), "SEM-S03")
                for name, child in item.items():
                    visit(child, path + (key, name))

    visit(root, ())
    for ref in references:
        fragment = urllib.parse.unquote(ref[1:], errors="strict")
        if not fragment:
            path = ()
        elif fragment.startswith("/"):
            path = tuple(
                part.replace("~1", "/").replace("~0", "~")
                for part in fragment[1:].split("/")
            )
        else:
            require(fragment in anchors, "SEM-S03")
            path = anchors[fragment]
        require(path in nodes, "SEM-S03")
    with tempfile.TemporaryDirectory(prefix="snapshot-schema-") as directory:
        paths = []
        # Check each schema node explicitly: the tool's bundled 2020-12
        # metaschema does not recursively check every nested schema keyword.
        for i, node in enumerate(nodes.values()):
            path = pathlib.Path(directory) / f"node-{i}.schema.json"
            path.write_bytes(emitted(node))
            paths.append(str(path))
        checked = subprocess.run(
            [
                "goneat",
                "schema",
                "validate-schema",
                "--format",
                "json",
                "--schema-id",
                "json-schema-2020-12",
                *paths,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        require(metaschema_result(checked, paths), "SEM-S03")


def metaschema_result(result: subprocess.CompletedProcess, paths: list[str]) -> bool:
    """Only recognized instance-validation diagnostics can satisfy a negative."""
    try:
        records = json.loads(result.stdout)
        assert result.returncode in {0, 1} and isinstance(records, list)
        assert len(records) == len(paths)
        assert {record["file"] for record in records} == set(paths)
        for record in records:
            assert record["schema_id"] == "json-schema-2020-12"
            assert type(record["valid"]) is bool
            if not record["valid"]:
                assert record.get("errors")
                for error in record["errors"]:
                    _, message = error.split(": ", 1)
                    assert (
                        message.startswith(
                            (
                                "Must ",
                                "must ",
                                "Invalid type",
                                "Additional property",
                                "String ",
                                "Array ",
                            )
                        )
                        or " must be " in message
                        or message.endswith(" is required")
                    )
        valid = all(record["valid"] for record in records)
        assert (result.returncode == 0) == valid
        return valid
    except (ValueError, KeyError, TypeError, AssertionError):
        raise RuntimeError(
            "metaschema tool failure: " + result.stdout + result.stderr
        ) from None


@functools.lru_cache(maxsize=256)
def valid_fixture_row(schema: bytes, row: bytes) -> bool:
    with tempfile.TemporaryDirectory(prefix="snapshot-row-") as directory:
        root = pathlib.Path(directory)
        path = root / "rows.schema.json"
        path.write_bytes(schema)
        return schema_check(row, path, root / "row.json")


def verify(store: dict[str, bytes], request: dict) -> None:
    metadata = set()

    def resolve(ref: dict, *, data: bool = False) -> bytes:
        require(ref["ref"] in store, "SEM-S02")
        raw = store[ref["ref"]]
        if not data:
            metadata.add(ref["ref"])
            require(sum(len(store[key]) for key in metadata) <= 67108864, "SEM-S08")
        require(len(raw) == ref["byte_length"], "SEM-S02")
        require(hashlib.sha256(raw).hexdigest() == ref["sha256"], "SEM-S02")
        return raw

    publication = parse(resolve(request["publication"]))
    require(publication["publication_id"] == request["publication"]["id"], "SEM-S01")
    require(publication["selection"] == request["selection"], "SEM-S01")
    manifest = parse(resolve(publication["manifest"]))
    descriptor = parse(resolve(publication["descriptor"]))
    profile = parse(resolve(publication["profile"]))
    require(publication["profile"] == request["profile"], "SEM-S07")
    require(profile["profile_id"] == publication["profile"]["id"], "SEM-S01")
    require(manifest["profile"] == publication["profile"], "SEM-S01")
    require(manifest["selection"] == publication["selection"], "SEM-S01")
    require(
        publication["manifest"]["id"] == manifest["selection"]["snapshot_id"], "SEM-S01"
    )
    require(
        publication["descriptor"]["id"]
        == descriptor["artifact_id"]
        == request["selection"]["artifact_id"],
        "SEM-S01",
    )
    require(
        publication["state"] == "committed"
        and descriptor["lifecycle"] in {"complete", "partial"},
        "SEM-S05",
    )
    require(request["operation"] in profile["operations"], "SEM-S07")
    require(manifest["count_relation"] in profile["count_relations"], "SEM-S07")
    require(manifest["physical_order"] in profile["physical_orders"], "SEM-S07")
    resolve(profile["semantic_spec"])
    if profile["retention"] == "profile_defined":
        resolve(profile["retention_spec"])
    row_schema_bytes = resolve(manifest["row_schema"])
    row_schema = parse(row_schema_bytes)
    catalog = parse(resolve(manifest["field_catalog"]))
    require(row_schema["$id"] == manifest["row_schema"]["schema_id"], "SEM-S01")
    check_row_schema(row_schema_bytes)
    require(catalog["id"] == manifest["field_catalog"]["id"], "SEM-S01")
    require(catalog["grain"] == manifest["grain_id"], "SEM-S01")
    grains = [g for g in descriptor["grains"] if g["id"] == manifest["grain_id"]]
    reps = [
        r
        for r in descriptor["representations"]
        if r["id"] == manifest["representation_id"]
    ]
    require(len(grains) == len(reps) == 1, "SEM-S03")
    grain, rep = grains[0], reps[0]
    require(rep["grain"] == grain["id"], "SEM-S01")
    require(rep["uri"] == publication["manifest"]["ref"], "SEM-S01")
    require(rep["profile"] == profile["profile_id"], "SEM-S01")
    require(
        grain.get("field_catalog_ref") == rep.get("field_catalog_ref") == catalog["id"],
        "SEM-S01",
    )
    for embedded in descriptor.get("field_catalogs", []):
        if embedded["id"] == catalog["id"]:
            require(embedded == catalog, "SEM-S01")
    require(rep["read_path"]["appendable"] is False, "SEM-S05")
    require(
        rep["read_path"].get("physical_ordering") == manifest["physical_order"],
        "SEM-S01",
    )
    members = manifest["members"]
    ids = [member["id"] for member in members]
    refs = [member["ref"] for member in members]
    require(len(set(ids)) == len(ids) and len(set(refs)) == len(refs), "SEM-S03")
    require(not set(refs).intersection(metadata), "SEM-S03")
    require(bool(members) or profile["empty_snapshots"], "SEM-S07")
    physical = sum(member["row_count"] for member in members)
    require(
        physical <= SAFE_INTEGER
        and physical == manifest["physical_row_count"] == rep.get("row_count"),
        "SEM-S04",
    )
    require(isinstance(grain.get("row_count"), int), "SEM-S04")
    require(
        physical == grain["row_count"]
        if manifest["count_relation"] == "equal"
        else physical <= grain["row_count"],
        "SEM-S04",
    )
    require(
        manifest["coverage_subject_uri"] == subject_uri(manifest["selection"]),
        "SEM-S06",
    )
    limits = profile["limits"]
    require(len(members) <= limits["max_members"], "SEM-S08")
    require(
        all(m["byte_length"] <= limits["max_member_bytes"] for m in members), "SEM-S08"
    )
    result = parse(store["artifact:result"])
    require(result["selection"] == request["selection"], "SEM-S01")
    require(
        result["publication"] == request["publication"]
        and result["manifest"] == publication["manifest"]
        and result["profile"] == publication["profile"],
        "SEM-S01",
    )
    require(
        result["operation"] == request["operation"]
        and result["scope"] == request["scope"],
        "SEM-S09",
    )
    require(result["requested_member_ids"] == request["member_ids"], "SEM-S09")
    requested = (
        set(request["member_ids"])
        if request["scope"] == "selected_members"
        else set(ids)
    )
    require(requested <= set(ids), "SEM-S09")
    if request["operation"] in {"full_scan", "full_verify"}:
        require(request["scope"] == "full_snapshot", "SEM-S09")
    if request["operation"] == "selective_verify":
        require(request["scope"] == "selected_members", "SEM-S09")
    verified = set(result["verified_member_ids"])
    require(verified <= requested, "SEM-S09")
    if result["outcome"] == "verified":
        require(verified == requested, "SEM-S09")
    if result["output_state"] == "provisional":
        require(profile["streaming"] == "provisional_until_terminal", "SEM-S10")
    checked_keys = []
    for member in members:
        if member["id"] in verified:
            raw = resolve(member, data=True)
            require(len(raw.splitlines()) == member["row_count"], "SEM-S04")
            for line in raw.splitlines():
                try:
                    row = parse(line)
                except (ValueError, UnicodeError, Violation):
                    raise Violation("SEM-S04") from None
                require(
                    isinstance(row, dict) and set(row) == {"key", "value"}, "SEM-S04"
                )
                require(
                    isinstance(row["key"], str) and type(row["value"]) is int, "SEM-S04"
                )
                require(valid_fixture_row(row_schema_bytes, line), "SEM-S04")
                checked_keys.append(row["key"])
    require(checked_keys == sorted(set(checked_keys)), "SEM-S04")
    if "coverage_attestation" in result:
        coverage = parse(resolve(result["coverage_attestation"]))
        require(
            coverage["attestation_id"] == result["coverage_attestation"]["id"],
            "SEM-S06",
        )
        require(
            coverage["subject"]
            == {
                "artifact_id": descriptor["artifact_id"],
                "grain_id": manifest["grain_id"],
                "subject_uri": manifest["coverage_subject_uri"],
            },
            "SEM-S06",
        )
    require(
        sum(len(store[key]) for key in metadata) <= limits["max_metadata_bytes"],
        "SEM-S08",
    )


def schema_check(raw: bytes, schema: pathlib.Path, tmp: pathlib.Path) -> bool:
    tmp.write_bytes(raw)
    if "#" in str(schema):
        filename, fragment = str(schema).split("#", 1)
        source = parse(pathlib.Path(filename).read_bytes())
        schema = tmp.parent / "catalog-wrapper.schema.json"
        schema.write_bytes(
            emitted(
                {
                    "$schema": source["$schema"],
                    "$defs": source["$defs"],
                    "$ref": "#" + fragment,
                }
            )
        )
    refs = ["--ref-dir", str(FAMILY)] if schema.parent == FAMILY else []
    result = subprocess.run(
        [
            "goneat",
            "validate",
            "data",
            "--schema-file",
            str(schema),
            *refs,
            "--data",
            str(tmp),
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
        assert result.returncode == 1
        # Goneat emits data-validation JSON to stderr before its CLI error.
        report, end = json.JSONDecoder().raw_decode(result.stderr.lstrip())
        assert report["valid"] is False and report["errors"]
        assert all(
            isinstance(item["path"], str) and isinstance(item["message"], str)
            for item in report["errors"]
        )
        assert (
            result.stderr.lstrip()[end:]
            .lstrip()
            .startswith("Error: data validation failed\n")
        )
        return False
    except (ValueError, KeyError, TypeError, AssertionError):
        raise RuntimeError(
            "schema validator setup/execution failure: " + result.stdout + result.stderr
        ) from None


def rebind(store: dict[str, bytes]) -> None:
    """Make mutated semantic cases byte-consistent; never fix the golden files."""

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if {"ref", "sha256", "byte_length"} <= value.keys() and value[
                "ref"
            ] in store:
                raw = store[value["ref"]]
                value["sha256"] = hashlib.sha256(raw).hexdigest()
                value["byte_length"] = len(raw)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for ref in (
        "artifact:profile",
        "artifact:manifest",
        "artifact:publication",
        "artifact:result",
    ):
        value = parse(store[ref])
        walk(value)
        store[ref] = emitted(value)


def mutate(store: dict[str, bytes], request: dict, edit: dict) -> None:
    target = edit["target"]
    if edit["op"] == "omit":
        del store[target]
        return
    if edit["op"] == "raw":
        store[target] = edit["value"].encode()
        return
    if edit["op"] == "reencode":
        store[target] = json.dumps(
            parse(store[target]), sort_keys=True, separators=(",", ":")
        ).encode()
        return
    value = request if target == "request" else parse(store[target])
    parent = value
    for key in edit["path"][:-1]:
        parent = parent[key]
    key = edit["path"][-1]
    if edit["op"] == "remove":
        del parent[key]
    else:
        parent[key] = copy.deepcopy(edit["value"])
    if target != "request":
        store[target] = emitted(value)


def main() -> None:
    contract = parse((FAMILY / "contract.json").read_bytes())
    assert contract["capability"] == CAPABILITY
    assert contract["entry_schema"] == "snapshot-publication.schema.json"
    for path in FAMILY.glob("*.schema.json"):
        assert (
            parse(path.read_bytes())["$id"]
            == "contract:segmented-snapshot/v0/" + path.name
        )
    base = {ref: (BASE / name).read_bytes() for ref, name in FILES.items()}
    base_result = parse(base["artifact:result"])
    request_base = {
        "selection": base_result["selection"],
        "publication": base_result["publication"],
        "profile": base_result["profile"],
        "operation": "full_verify",
        "scope": "full_snapshot",
        "member_ids": [],
    }
    cases = parse((FAMILY / "fixtures/cases.json").read_bytes())["cases"]
    assert len({case["name"] for case in cases}) == len(cases)
    with tempfile.TemporaryDirectory(prefix="snapshot-controls-") as directory:
        tmp = pathlib.Path(directory) / "instance.json"
        for code, diagnostic in (
            (1, "metaschema unavailable"),
            (-9, "terminated"),
            (1, "validation failed: duplicate schema $id"),
        ):
            failure = subprocess.CompletedProcess([], code, "", diagnostic)
            with mock.patch.object(subprocess, "run", return_value=failure):
                for probe in (
                    lambda: check_row_schema.__wrapped__(base["artifact:row-schema"]),
                    lambda: schema_check(
                        base["artifact:profile"], SCHEMAS["artifact:profile"], tmp
                    ),
                ):
                    try:
                        probe()
                    except RuntimeError:
                        pass
                    else:
                        raise AssertionError(
                            "tool failure counted as validation evidence"
                        )
        print("[ok] tool failures cannot satisfy semantic or structural negatives")
        for ref, schema in SCHEMAS.items():
            assert schema_check(base[ref], schema, tmp), (
                f"baseline structural failure: {ref}"
            )
        verify(base, request_base)
        print("[ok] exact committed baseline; partial lifecycle with valid publication")
        for case in cases:
            store, request = copy.deepcopy(base), copy.deepcopy(request_base)
            if "selection" in case:
                request["selection"] = copy.deepcopy(case["selection"])
                for ref in (
                    "artifact:manifest",
                    "artifact:publication",
                    "artifact:result",
                ):
                    value = parse(store[ref])
                    value["selection"] = copy.deepcopy(case["selection"])
                    if "manifest" in value:
                        value["manifest"]["id"] = case["selection"]["snapshot_id"]
                    if "coverage_subject_uri" in value:
                        value["coverage_subject_uri"] = case["subject_uri"]
                    store[ref] = emitted(value)
                coverage = parse(store["artifact:coverage"])
                coverage["subject"]["subject_uri"] = case["subject_uri"]
                store["artifact:coverage"] = emitted(coverage)
            for edit in case["edits"]:
                mutate(store, request, edit)
            if case.get("rebind", False):
                rebind(store)
                if "metadata_limit" in case:
                    # Independent positive/exact-boundary construction. This is
                    # fixture emission, not the verifier's metadata accounting.
                    refs = set(FILES) - {
                        "artifact:member-a",
                        "artifact:member-b",
                        "artifact:result",
                        "artifact:retention-spec",
                    }
                    for _ in range(8):
                        profile = parse(store["artifact:profile"])
                        limit = (
                            sum(len(store[ref]) for ref in refs)
                            + case["metadata_limit"]
                        )
                        if profile["limits"]["max_metadata_bytes"] == limit:
                            break
                        profile["limits"]["max_metadata_bytes"] = limit
                        store["artifact:profile"] = emitted(profile)
                        rebind(store)
                    else:
                        raise AssertionError(
                            "fixture metadata bound failed to stabilize"
                        )
                request["publication"] = binding(
                    store["artifact:publication"],
                    "artifact:publication",
                    "publication-1",
                )
                request["profile"] = parse(store["artifact:publication"])["profile"]
            if case["expect"] == "structural_rejection":
                ref = case["structural_target"]
                assert not schema_check(store[ref], SCHEMAS[ref], tmp), (
                    f"structural negative accepted: {case['name']}"
                )
            else:
                changed = {
                    edit["target"]
                    for edit in case["edits"]
                    if edit["op"] not in {"omit", "raw", "reencode"}
                }
                for ref in changed.intersection(SCHEMAS):
                    assert schema_check(store[ref], SCHEMAS[ref], tmp), (
                        f"semantic case failed shape: {case['name']} / {ref}"
                    )
                actual = "pass"
                try:
                    verify(store, request)
                except Violation as error:
                    actual = str(error)
                assert actual == case["expect"], (
                    f"{case['name']}: expected {case['expect']}, got {actual}"
                )
            print(f"[ok] {case['name']}: {case['expect']}")
    try:
        parse(b'{"x":1,"x":2}')
    except Violation as error:
        assert str(error) == "SEM-S00"
    else:
        raise AssertionError("duplicate JSON members accepted")
    print(
        f"Segmented snapshot: baseline + {len(cases)} controls and duplicate-member rejection PASS"
    )


if __name__ == "__main__":
    main()
