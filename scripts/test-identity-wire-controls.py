#!/usr/bin/env python3
"""Independent witnesses for bounded identity wire vectors, not a verifier."""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

EXPECTED_IDS = {
    "ordinary-object",
    "numeric-equivalence",
    "unicode-key-order",
    "escaped-member-collision",
    "nested-member-collision",
    "lone-surrogate",
    "noncharacter",
    "invalid-utf8",
    "imprecise-integer",
    "nonfinite-number",
    "trailing-json",
    "empty-input",
    "exact-raw-cap",
    "over-raw-cap",
    "exact-depth",
    "over-depth",
    "canonical-expansion",
}


def refuse(code):
    raise ValueError(code)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            refuse("duplicate_member")
        result[key] = value
    return result


def encode_input(case):
    kind = case["kind"]
    if kind == "raw":
        return case["raw"].encode("utf-8")
    if kind == "hex":
        return bytes.fromhex(case["hex"])
    if kind == "padded-object":
        return b"{}" + b" " * (case["bytes"] - 2)
    if kind == "nested-array":
        return b"[" * case["depth"] + b"0" + b"]" * case["depth"]
    if kind == "number-array":
        return b"[" + b",".join([b"1e20"] * case["count"]) + b"]"
    refuse("unknown-vector-input")


def witness(raw, jcs):
    if len(raw) > 262144:
        refuse("report-too-large")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        refuse("invalid_utf8")
    # Scan depth before constructing the JSON value. Strings/escapes do not
    # count as containers. This is a bounded witness, not a general lexer.
    depth = 0
    quoted = escaped = False
    for ch in text:
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch in "[{":
            depth += 1
            if depth > 16:
                refuse("too_deep")
        elif ch in "]}":
            depth -= 1
    try:
        value = json.loads(
            text,
            object_pairs_hook=unique,
            parse_constant=lambda _: refuse("invalid_json"),
        )
    except json.JSONDecodeError:
        refuse("invalid_json")

    def domain(v):
        if isinstance(v, str):
            for ch in v:
                cp = ord(ch)
                if 0xD800 <= cp <= 0xDFFF:
                    refuse("lone_surrogate")
                if 0xFDD0 <= cp <= 0xFDEF or cp & 0xFFFF in (0xFFFE, 0xFFFF):
                    refuse("noncharacter")
        elif isinstance(v, dict):
            for key, item in v.items():
                domain(key)
                domain(item)
        elif isinstance(v, list):
            for item in v:
                domain(item)
        elif type(v) is int:
            try:
                exact = math.isfinite(float(v)) and int(float(v)) == v
            except OverflowError:
                exact = False
            if not exact:
                refuse("integer_outside_binary64")
        elif type(v) is float and not math.isfinite(v):
            refuse("non_finite_number")

    domain(value)
    out = jcs.jcs_dumps(value).encode("utf-8")
    if len(out) > 262144:
        refuse("canonical-report-too-large")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    root = args.root
    spec = importlib.util.spec_from_file_location(
        "jcs", root / "scripts/rfc8785-canonicalize.py"
    )
    jcs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jcs)
    family = root / "schemas/identity-evidence/v0"
    pack = json.loads((family / "vectors/wire-admission.json").read_text())
    ids = [case["id"] for case in pack["cases"]]
    assert len(ids) == len(set(ids)) and set(ids) == EXPECTED_IDS, (
        "vector inventory differs"
    )
    for case in pack["cases"]:
        try:
            out = witness(encode_input(case), jcs)
        except ValueError as exc:
            actual = str(exc)
        else:
            actual = "accept"
            if "canonical" in case:
                assert out == case["canonical"].encode("utf-8"), (
                    case["id"] + ": canonical mismatch"
                )
        assert actual == case["expected"], (
            f"{case['id']}: {actual}, expected {case['expected']}"
        )
    for path in (family / "examples").glob("*.json"):
        witness(path.read_bytes(), jcs)
    if not args.check_only:
        source = Path(__file__).read_text()
        mutants = [
            (
                "raw-cap",
                "if len(raw) > 262144:",
                "if False and len(raw) > 262144:",
                "over-raw-cap",
            ),
            (
                "duplicate-member",
                "if key in result:",
                "if False and key in result:",
                "escaped-member-collision",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for name, old, new, detecting in mutants:
                assert old in source
                path = Path(tmp) / (name + ".py")
                path.write_text(source.replace(old, new, 1))
                result = subprocess.run(
                    [sys.executable, str(path), "--check-only", "--root", str(root)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                assert result.returncode != 0 and (detecting + ":") in result.stderr, (
                    "mutant escaped intended assertion: " + name
                )
    print(
        "PASS: 17 hand-authored wire cases, example byte/domain checks, raw-cap and duplicate-member mutation detection"
    )
    print(
        "Limited independent vector witness; not complete canonicalization or adopter qualification."
    )


if __name__ == "__main__":
    main()
