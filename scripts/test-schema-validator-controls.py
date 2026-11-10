#!/usr/bin/env python3
"""Exercise the active validator's report, format and raw JSON profile."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


PROFILE_FIELDS = ("engine", "dialect", "dialect_source", "format_mode", "leap_policy")
DIALECT = "https://json-schema.org/draft/2020-12/schema"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def report_from(proc):
    # Some releases write reports to stderr, followed by CLI usage on failure.
    for stream in (proc.stdout, proc.stderr):
        try:
            value, _ = json.JSONDecoder().raw_decode(stream.lstrip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("valid"), bool):
            return value
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goneat", default=shutil.which("goneat"))
    parser.add_argument("--require-metadata", action="store_true")
    args = parser.parse_args()
    require(args.goneat, "goneat is required")
    binary = Path(args.goneat).resolve()
    passed = 0

    with tempfile.TemporaryDirectory(prefix="schema-validator-") as tmp:
        root = Path(tmp)
        schema_path = root / "schema.json"
        data_path = root / "data.json"

        def probe(label, schema, raw, expected, *, admission=False):
            nonlocal passed
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            data_path.write_bytes(
                raw if isinstance(raw, bytes) else raw.encode("utf-8")
            )
            proc = subprocess.run(
                [
                    str(binary),
                    "schema",
                    "validate-data",
                    "--schema-file",
                    str(schema_path),
                    "--data",
                    str(data_path),
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            report = report_from(proc)
            if admission:
                require(
                    proc.returncode != 0 and report is None,
                    f"{label}: expected schema admission failure",
                )
            elif expected is None:
                require(
                    proc.returncode != 0 and not (report or {}).get("valid"),
                    f"{label}: expected raw JSON parse failure",
                )
            else:
                require(report is not None, f"{label}: missing validation report")
                require(report["valid"] is expected, f"{label}: wrong verdict {report}")
                require(
                    proc.returncode == (0 if expected else 1),
                    f"{label}: unexpected exit {proc.returncode}",
                )
            passed += 1
            return report

        string_schema = {"$schema": DIALECT, "type": "string"}
        profile = probe("report-positive", string_schema, '"ordinary"', True)
        probe("report-negative", string_schema, "42", False)
        present = [key for key in PROFILE_FIELDS if key in profile]
        require(
            not present or len(present) == len(PROFILE_FIELDS),
            "partial validator metadata is not a qualified profile",
        )
        require(not args.require_metadata or present, "validator metadata required")

        if present:
            require(
                all(
                    isinstance(profile[key], str) and profile[key]
                    for key in PROFILE_FIELDS
                ),
                "empty validator metadata",
            )
            require(profile["dialect"] == "draft/2020-12", "wrong declared dialect")
            require(profile["dialect_source"] == "declared", "wrong dialect source")
            require(profile["format_mode"] == "assert", "formats must be asserted")
            require(
                profile["leap_policy"] == "structural-leap/v1",
                "leap policy changed; requalify the validator profile",
            )
            for fmt, valid, invalid in (
                ("date", "2026-02-28", "2026-02-30"),
                ("date-time", "2026-02-28T00:00:00Z", "2026-02-30T00:00:00Z"),
                ("time", "23:59:59Z", "25:00:00Z"),
                ("email", "reader@example.org", "not-an-address"),
            ):
                schema = {**string_schema, "format": fmt}
                probe(f"{fmt}-positive", schema, json.dumps(valid), True)
                probe(f"{fmt}-negative", schema, json.dumps(invalid), False)

            # Generic format policy differs from durable-record's stricter language.
            probe(
                "generic-structural-leap",
                {**string_schema, "format": "date-time"},
                '"2024-02-29T23:59:60Z"',
                True,
            )
            date_time = {**string_schema, "format": "date-time"}
            for label, value in (
                ("bare-date", "2026-10-12"),
                ("comma-fraction", "2026-10-12T14:30:59,1Z"),
                ("one-digit-hour", "2026-10-12T4:30:59Z"),
                ("offset-hour-24", "2026-10-12T14:30:59+24:00"),
            ):
                probe(label, date_time, json.dumps(value), False)
            for label, value in (
                ("lowercase-tz", "2026-10-12t14:30:59z"),
                ("negative-zero-offset", "2026-10-12T14:30:59-00:00"),
                ("extra-zero-fraction", "2026-10-12T14:30:59.123456000Z"),
            ):
                probe(label, date_time, json.dumps(value), True)
            probe(
                "unknown-format",
                {**string_schema, "format": "unknown-test-format"},
                '"ordinary"',
                False,
                admission=True,
            )
            unconstrained = {"$schema": DIALECT}
            probe("exact-large-number", unconstrained, "1e400", True)
            integer = {
                "$schema": DIALECT,
                "type": "integer",
                "maximum": 9007199254740991,
            }
            probe("large-bounded-integer", integer, "1e400", False)
            probe("fraction-near-safe-limit", integer, "9007199254740990.5", False)
            probe("safe-limit-integer", integer, "9007199254740991", True)
            probe("invalid-utf8", unconstrained, b'"\xff"', None)
            probe("lone-surrogate", unconstrained, b'"\\ud800"', None)
            probe("malformed-json", unconstrained, "{", None)
        else:
            print(
                "[ok] legacy report profile; strict-decoder/format metadata controls deferred"
            )

    version = subprocess.run(
        [str(binary), "version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    require(version.returncode == 0, "validator identity command failed")
    print(
        json.dumps(
            {
                "controls": passed,
                "profile": {
                    key: profile[key] for key in PROFILE_FIELDS if key in profile
                },
                "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                "version": version.stdout.strip(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
