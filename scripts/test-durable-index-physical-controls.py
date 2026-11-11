#!/usr/bin/env python3
"""Bind durable-index physical fixture bytes to fixed authored logical twins.

This is a repository-corpus integrity and logical-oracle control.  It does not
decode Parquet, qualify a physical reader, or make an R2/W claim.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "schemas/durable-index/v0/fixtures/parquet-inventory"
MANIFEST_NAME = "manifest.json"
CONTROL_FILES = {MANIFEST_NAME, "README.md"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def load_checker():
    path = ROOT / "scripts/test-durable-index-controls.py"
    spec = importlib.util.spec_from_file_location("durable_index_logical", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECKER = load_checker()


class Refusal(Exception):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Refusal(reason)


def strict_json(raw: bytes, reason: str) -> Any:
    try:
        return CHECKER.strict(raw)
    except CHECKER.Refusal as exc:
        raise Refusal(reason) from exc


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def safe_id(value: Any) -> bool:
    return isinstance(value, str) and ID_RE.fullmatch(value) is not None


def safe_hash(value: Any) -> bool:
    return isinstance(value, str) and HEX_RE.fullmatch(value) is not None


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def artifact_schema(artifact: Any, reasons: set[str]) -> bool:
    if not isinstance(artifact, dict) or not safe_id(artifact.get("id")):
        return False
    negative = "expected_refusal" in artifact
    if negative:
        return (
            set(artifact)
            == {"id", "parquet_sha256", "parquet_byte_length", "expected_refusal"}
            and safe_hash(artifact["parquet_sha256"])
            and positive_int(artifact["parquet_byte_length"])
            and isinstance(artifact["expected_refusal"], str)
            and artifact["expected_refusal"] in reasons
        )
    return (
        set(artifact)
        == {
            "id",
            "codec",
            "data_page_version",
            "size_bytes_annotation",
            "parquet_sha256",
            "parquet_byte_length",
            "logical_ndjson_sha256",
            "logical_ndjson_byte_length",
            "row_count",
        }
        and isinstance(artifact["codec"], str)
        and artifact["codec"] in {"zstd", "uncompressed"}
        and type(artifact["data_page_version"]) is int
        and artifact["data_page_version"] in {1, 2}
        and isinstance(artifact["size_bytes_annotation"], str)
        and artifact["size_bytes_annotation"] in {"int64_signed", "absent"}
        and safe_hash(artifact["parquet_sha256"])
        and safe_hash(artifact["logical_ndjson_sha256"])
        and all(
            positive_int(artifact[name])
            for name in (
                "parquet_byte_length",
                "logical_ndjson_byte_length",
                "row_count",
            )
        )
    )


def provenance_schema(value: Any) -> bool:
    fields = {
        "repository",
        "revision",
        "generator",
        "reader",
        "go_version",
        "parquet_go_version",
        "invocation",
        "oracle_sha256",
    }
    return (
        isinstance(value, dict)
        and set(value) == fields
        and all(nonempty_string(value[field]) for field in fields)
        and REVISION_RE.fullmatch(value["revision"]) is not None
        and safe_hash(value["oracle_sha256"])
    )


def read_rows(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    require(raw.endswith(b"\n") and b"\r" not in raw, "logical_ndjson_framing")
    lines = raw.splitlines()
    require(
        bool(lines) and all(line.strip() for line in lines), "logical_ndjson_framing"
    )
    rows = []
    for line in lines:
        row = strict_json(line, "logical_ndjson_parse")
        # JSON's default float materialization would round 9007199254740991.1
        # and underflow 1e-400 before rows_valid reserializes the value. Validate
        # the original numeric spelling against the row schema first.
        require(CHECKER.shaped(line, "index-row.schema.json"), "invalid_shape")
        rows.append(row)
    require(all(isinstance(row, dict) for row in rows), "logical_row_shape")
    try:
        CHECKER.rows_valid(rows)
    except CHECKER.Refusal as exc:
        raise Refusal(str(exc)) from exc
    return rows


def validate(corpus: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    require(corpus.is_dir() and not corpus.is_symlink(), "corpus_root")
    entries = list(corpus.iterdir())
    require(
        all(not entry.is_symlink() and entry.is_file() for entry in entries),
        "corpus_layout",
    )
    names = {entry.name for entry in entries}
    require(CONTROL_FILES <= names, "corpus_control_files")
    manifest = strict_json((corpus / MANIFEST_NAME).read_bytes(), "manifest_parse")
    require(isinstance(manifest, dict), "manifest_shape")
    require(
        set(manifest)
        == {
            "version",
            "profile",
            "provenance",
            "artifacts",
            "member_sets",
            "logical_oracle",
        },
        "manifest_shape",
    )
    require(
        type(manifest["version"]) is int
        and manifest["version"] == 1
        and manifest["profile"] == "parquet-inventory/v0",
        "manifest_identity",
    )
    require(
        isinstance(manifest["provenance"], list) and manifest["provenance"],
        "provenance",
    )
    require(
        all(provenance_schema(item) for item in manifest["provenance"]), "provenance"
    )
    require(
        isinstance(manifest["artifacts"], list) and manifest["artifacts"], "artifacts"
    )
    reasons = CHECKER.declared_reasons()
    require(
        all(artifact_schema(item, reasons) for item in manifest["artifacts"]),
        "artifact_shape",
    )
    ids = [item["id"] for item in manifest["artifacts"]]
    require(len(ids) == len(set(ids)), "duplicate_artifact_id")
    positive = {
        item["id"]: item
        for item in manifest["artifacts"]
        if "expected_refusal" not in item
    }
    require(positive, "artifacts")
    require(
        safe_id(manifest["logical_oracle"]) and manifest["logical_oracle"] in positive,
        "logical_oracle",
    )
    logical_oracle = positive[manifest["logical_oracle"]]
    require(
        all(
            item["oracle_sha256"] == logical_oracle["logical_ndjson_sha256"]
            for item in manifest["provenance"]
        ),
        "provenance_oracle",
    )
    expected_files = set(CONTROL_FILES)
    rows_by_id: dict[str, list[dict[str, Any]]] = {}
    matrix = {"codec": set(), "page": set(), "annotation": set()}
    for artifact in manifest["artifacts"]:
        parquet_name = artifact["id"] + ".parquet"
        parquet = corpus / parquet_name
        require(parquet.is_file() and not parquet.is_symlink(), "physical_missing")
        raw = parquet.read_bytes()
        require(len(raw) == artifact["parquet_byte_length"], "physical_byte_length")
        require(sha256(raw) == artifact["parquet_sha256"], "physical_digest")
        expected_files.add(parquet_name)
        if artifact["id"] not in positive:
            continue
        twin_name = artifact["id"] + ".ndjson"
        twin = corpus / twin_name
        require(twin.is_file() and not twin.is_symlink(), "logical_twin_missing")
        twin_raw = twin.read_bytes()
        require(
            len(twin_raw) == artifact["logical_ndjson_byte_length"],
            "logical_twin_byte_length",
        )
        require(
            sha256(twin_raw) == artifact["logical_ndjson_sha256"], "logical_twin_digest"
        )
        rows = read_rows(twin)
        require(len(rows) == artifact["row_count"], "logical_row_count")
        rows_by_id[artifact["id"]] = rows
        expected_files.add(twin_name)
        matrix["codec"].add(artifact["codec"])
        matrix["page"].add(artifact["data_page_version"])
        matrix["annotation"].add(artifact["size_bytes_annotation"])
    require(names == expected_files, "corpus_inventory")
    require(matrix["codec"] == {"zstd", "uncompressed"}, "profile_matrix")
    require(matrix["page"] == {1, 2}, "profile_matrix")
    require(matrix["annotation"] == {"int64_signed", "absent"}, "profile_matrix")
    require(
        isinstance(manifest["member_sets"], list) and manifest["member_sets"],
        "member_sets",
    )
    set_ids: set[str] = set()
    multi_member = False
    covered_members: list[str] = []
    for member_set in manifest["member_sets"]:
        require(
            isinstance(member_set, dict)
            and set(member_set) == {"id", "members", "logical_twin"},
            "member_set_shape",
        )
        require(
            safe_id(member_set["id"]) and member_set["id"] not in set_ids,
            "member_set_id",
        )
        set_ids.add(member_set["id"])
        members = member_set["members"]
        require(
            isinstance(members, list)
            and members
            and all(safe_id(member) and member in positive for member in members),
            "member_set_members",
        )
        require(len(members) == len(set(members)), "member_set_members")
        require(
            safe_id(member_set["logical_twin"])
            and member_set["logical_twin"] == manifest["logical_oracle"],
            "member_set_twin",
        )
        actual = [row for member in members for row in rows_by_id[member]]
        try:
            CHECKER.rows_valid(actual)
        except CHECKER.Refusal as exc:
            raise Refusal(str(exc)) from exc
        require(actual == rows_by_id[manifest["logical_oracle"]], "logical_twin_parity")
        covered_members.extend(members)
        multi_member = multi_member or len(members) >= 2
    require(multi_member, "member_set_coverage")
    require(
        len(covered_members) == len(set(covered_members))
        and set(covered_members) == set(positive),
        "member_set_coverage",
    )
    return manifest, rows_by_id


def update_pin(artifact: dict[str, Any], name: str, raw: bytes) -> None:
    artifact[f"{name}_sha256"] = sha256(raw)
    artifact[f"{name}_byte_length"] = len(raw)


def mutation_controls() -> None:
    def refuse(name: str, expected: str, mutate) -> None:
        with tempfile.TemporaryDirectory(prefix="durable-index-physical-") as directory:
            target = Path(directory) / "corpus"
            shutil.copytree(CORPUS, target)
            mutate(target)
            try:
                validate(target)
            except Refusal as exc:
                assert str(exc) == expected, (name, str(exc), expected)
                print(f"[ok] mutation detected: {name}")
            else:
                raise AssertionError(f"mutation accepted: {name}")

    def accept(name: str, mutate) -> None:
        with tempfile.TemporaryDirectory(prefix="durable-index-physical-") as directory:
            target = Path(directory) / "corpus"
            shutil.copytree(CORPUS, target)
            mutate(target)
            validate(target)
            print(f"[ok] accepted spelling: {name}")

    manifest = strict_json((CORPUS / MANIFEST_NAME).read_bytes(), "manifest_parse")
    by_id = {artifact["id"]: artifact for artifact in manifest["artifacts"]}
    oracle_id = manifest["logical_oracle"]
    first = by_id[oracle_id]
    boundary = next(
        member_set
        for member_set in manifest["member_sets"]
        if len(member_set["members"]) >= 2
    )
    first_member = by_id[boundary["members"][0]]
    second_member = by_id[boundary["members"][1]]
    noncanonical_full = next(
        member_set
        for member_set in manifest["member_sets"]
        if len(member_set["members"]) == 1 and member_set["members"][0] != oracle_id
    )
    noncanonical_full_id = noncanonical_full["members"][0]

    def rewrite(target: Path, change) -> None:
        value = json.loads((target / MANIFEST_NAME).read_text())
        change(value)
        (target / MANIFEST_NAME).write_text(json.dumps(value, indent=2) + "\n")

    def target_artifact(value: dict[str, Any], artifact_id: str) -> dict[str, Any]:
        return next(item for item in value["artifacts"] if item["id"] == artifact_id)

    def update_provenance_oracle(value: dict[str, Any], raw: bytes) -> None:
        for provenance in value["provenance"]:
            provenance["oracle_sha256"] = sha256(raw)

    def manifest_mutation(name: str, expected: str, edit) -> None:
        def mutate(target: Path) -> None:
            rewrite(target, edit)

        refuse(name, expected, mutate)

    def update_first(field: str, replacement: Any):
        def edit(value: dict[str, Any]) -> None:
            target_artifact(value, first["id"])[field] = replacement

        return edit

    def change_physical_byte(target: Path) -> None:
        path = target / (first["id"] + ".parquet")
        path.write_bytes(b"x" + path.read_bytes()[1:])

    def change_physical_pin(value: dict[str, Any]) -> None:
        target_artifact(value, first["id"])["parquet_sha256"] = "0" * 64

    def change_physical_length(value: dict[str, Any]) -> None:
        target_artifact(value, first["id"])["parquet_byte_length"] += 1

    def duplicate_artifact_id(value: dict[str, Any]) -> None:
        value["artifacts"][1]["id"] = value["artifacts"][0]["id"]

    refuse(
        "missing-physical",
        "physical_missing",
        lambda target: (target / (first["id"] + ".parquet")).unlink(),
    )
    refuse(
        "extra-file",
        "corpus_inventory",
        lambda target: (target / "unlisted.parquet").write_bytes(b"x"),
    )
    refuse("changed-physical-byte", "physical_digest", change_physical_byte)
    manifest_mutation("changed-physical-pin", "physical_digest", change_physical_pin)
    manifest_mutation(
        "changed-physical-length", "physical_byte_length", change_physical_length
    )
    manifest_mutation(
        "duplicate-artifact-id", "duplicate_artifact_id", duplicate_artifact_id
    )
    manifest_mutation(
        "unsafe-artifact-id", "artifact_shape", update_first("id", "../escape")
    )
    manifest_mutation(
        "wrong-row-count",
        "logical_row_count",
        update_first("row_count", first["row_count"] + 1),
    )
    manifest_mutation(
        "closed-artifact-bool", "artifact_shape", update_first("row_count", True)
    )
    manifest_mutation(
        "version-bool", "manifest_identity", lambda value: value.update(version=True)
    )
    manifest_mutation(
        "version-float", "manifest_identity", lambda value: value.update(version=1.0)
    )
    manifest_mutation(
        "page-version-bool", "artifact_shape", update_first("data_page_version", True)
    )
    manifest_mutation(
        "page-version-float", "artifact_shape", update_first("data_page_version", 2.0)
    )
    manifest_mutation("artifact-id-number", "artifact_shape", update_first("id", 1))
    manifest_mutation(
        "artifact-hash-list", "artifact_shape", update_first("parquet_sha256", [])
    )
    manifest_mutation(
        "member-id-number",
        "member_set_members",
        lambda value: value["member_sets"][0].update(
            members=[1, *value["member_sets"][0]["members"][1:]]
        ),
    )
    manifest_mutation(
        "member-twin-list",
        "member_set_twin",
        lambda value: value["member_sets"][0].update(logical_twin=[]),
    )

    def malformed_twin(target: Path) -> None:
        path = target / (first["id"] + ".ndjson")
        raw = b"{not-json}\n"
        path.write_bytes(raw)

        def edit(value: dict[str, Any]) -> None:
            update_pin(target_artifact(value, first["id"]), "logical_ndjson", raw)
            update_provenance_oracle(value, raw)

        rewrite(target, edit)

    refuse("malformed-logical-twin-repinned", "logical_ndjson_parse", malformed_twin)

    def semantic_twin(target: Path) -> None:
        path = target / (first["id"] + ".ndjson")
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["size_bytes"] = -1
        raw = b"".join(
            json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in rows
        )
        path.write_bytes(raw)

        def edit(value: dict[str, Any]) -> None:
            update_pin(target_artifact(value, first["id"]), "logical_ndjson", raw)
            update_provenance_oracle(value, raw)

        rewrite(target, edit)

    refuse("semantic-logical-twin-repinned", "invalid_shape", semantic_twin)

    def parity(target: Path) -> None:
        path = target / (second_member["id"] + ".ndjson")
        raw = (target / (first_member["id"] + ".ndjson")).read_bytes()
        path.write_bytes(raw)

        def edit(value: dict[str, Any]) -> None:
            artifact = target_artifact(value, second_member["id"])
            update_pin(artifact, "logical_ndjson", raw)
            artifact["row_count"] = 1

        rewrite(target, edit)

    refuse("cross-member-duplicate", "duplicate_key_row", parity)

    def logical_parity(target: Path) -> None:
        path = target / (noncanonical_full_id + ".ndjson")
        raw = path.read_bytes()
        assert raw.count(b"STANDARD") == 1
        raw = raw.replace(b"STANDARD", b"COLD")
        path.write_bytes(raw)
        rewrite(
            target,
            lambda value: update_pin(
                target_artifact(value, noncanonical_full_id), "logical_ndjson", raw
            ),
        )

    refuse("logical-twin-parity", "logical_twin_parity", logical_parity)

    def repin_noncanonical(target: Path, old: bytes, new: bytes) -> None:
        path = target / (noncanonical_full_id + ".ndjson")
        raw = path.read_bytes()
        assert raw.count(old) == 1
        raw = raw.replace(old, new)
        path.write_bytes(raw)
        rewrite(
            target,
            lambda value: update_pin(
                target_artifact(value, noncanonical_full_id), "logical_ndjson", raw
            ),
        )

    refuse(
        "fractional-safe-integer-repinned",
        "invalid_shape",
        lambda target: repin_noncanonical(
            target, b"9007199254740991", b"9007199254740991.1"
        ),
    )
    refuse(
        "underflow-repinned",
        "invalid_shape",
        lambda target: repin_noncanonical(
            target, b'"size_bytes":0', b'"size_bytes":1e-400'
        ),
    )
    accept(
        "safe-integer-decimal",
        lambda target: repin_noncanonical(
            target, b"9007199254740991", b"9007199254740991.0"
        ),
    )
    accept(
        "safe-integer-exponent",
        lambda target: repin_noncanonical(
            target, b"9007199254740991", b"9.007199254740991e15"
        ),
    )
    accept(
        "zero-decimal",
        lambda target: repin_noncanonical(
            target, b'"size_bytes":0', b'"size_bytes":0.0'
        ),
    )

    def reverse_boundary_order(value: dict[str, Any]) -> None:
        member_set = next(
            member_set
            for member_set in value["member_sets"]
            if member_set["id"] == boundary["id"]
        )
        member_set["members"] = list(reversed(member_set["members"]))

    manifest_mutation("cross-member-order", "row_order", reverse_boundary_order)

    def missing_coverage(value: dict[str, Any]) -> None:
        value["member_sets"] = [
            member_set
            for member_set in value["member_sets"]
            if member_set["id"] != noncanonical_full["id"]
        ]

    def duplicate_coverage(value: dict[str, Any]) -> None:
        member_set = next(
            member_set
            for member_set in value["member_sets"]
            if member_set["id"] == noncanonical_full["id"]
        )
        member_set["members"] = [oracle_id]

    manifest_mutation(
        "missing-member-coverage", "member_set_coverage", missing_coverage
    )
    manifest_mutation(
        "duplicate-member-coverage", "member_set_coverage", duplicate_coverage
    )


def main() -> None:
    manifest, rows = validate(CORPUS)
    mutation_controls()
    positive = sum(
        "expected_refusal" not in artifact for artifact in manifest["artifacts"]
    )
    negative = len(manifest["artifacts"]) - positive
    print(
        f"Durable-index physical corpus binding PASS: {positive} positive artifacts, "
        f"{negative} negative artifacts, {len(manifest['member_sets'])} member sets, "
        f"{sum(len(value) for value in rows.values())} logical twin rows."
    )
    print(
        "Binding and logical-oracle controls only; no Parquet decoding or R2/W qualification claim."
    )


if __name__ == "__main__":
    main()
