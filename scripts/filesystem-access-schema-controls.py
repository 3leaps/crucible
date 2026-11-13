#!/usr/bin/env python3
"""Repository schema controls; Goneat is the sole external validator invoked."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

FAMILY = Path(__file__).resolve().parents[1] / "schemas/filesystem-access/v0"
CONTRACT = "filesystem-access/v0"


def require(ok, label):
    if not ok:
        raise AssertionError(label)


def run_schema_controls():
    validator = shutil.which("goneat")
    require(validator is not None, "goneat is required for schema controls")
    count = 0
    failures = []
    with tempfile.TemporaryDirectory(prefix="filesystem-access-schema-") as directory:
        data = Path(directory) / "instance.json"

        def check(schema, value, expected, label):
            nonlocal count
            data.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")
            result = subprocess.run(
                [
                    validator,
                    "validate",
                    "data",
                    "--schema-file",
                    str(FAMILY / (schema + ".schema.json")),
                    "--ref-dir",
                    str(FAMILY),
                    "--data",
                    str(data),
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=30,
            )
            try:
                report, _ = json.JSONDecoder().raw_decode(
                    (result.stdout if result.stdout.strip() else result.stderr).lstrip()
                )
            except (ValueError, TypeError) as error:
                raise AssertionError(
                    f"{label}: validator did not return a report: {result.stderr[:500]}"
                ) from error
            if report.get("valid") is not expected:
                failures.append(
                    f"{label}: expected valid={expected}, got {report.get('valid')}"
                )
                count += 1
                return
            require(
                result.returncode == (0 if expected else 1),
                f"{label}: validator execution failure",
            )
            if not expected:
                require(
                    bool(report.get("errors")), f"{label}: refusal lacks schema errors"
                )
            count += 1

        request_base = {"contract": CONTRACT, "capabilities": {}}
        requests = [
            {**request_base, "operation": "open_root", "root_ref": "root:fixture"},
            {
                **request_base,
                "operation": "open_read",
                "root_handle": "handle:root",
                "lifetime_generation": 1,
                "profile": "no-links/v0",
                "name": "dir/file",
                "max_bytes": 5,
            },
            {
                **request_base,
                "operation": "create_exclusive",
                "root_handle": "handle:root",
                "lifetime_generation": 1,
                "profile": "containment/v0",
                "name": "dir/new",
            },
            {
                **request_base,
                "operation": "read_dir",
                "root_handle": "handle:root",
                "lifetime_generation": 1,
                "profile": "no-links/v0",
                "name": "dir",
                "max_entries": 5,
            },
            {
                **request_base,
                "operation": "stat",
                "handle": "handle:file",
                "lifetime_generation": 1,
            },
            {
                **request_base,
                "operation": "same_object",
                "left_handle": "handle:a",
                "left_generation": 1,
                "right_handle": "handle:b",
                "right_generation": 2,
            },
        ]
        for request in requests:
            op = request["operation"]
            check("access-request", request, True, op + " request")
            check(
                "access-request",
                {**request, "host_path": "/outside"},
                False,
                op + " host-path injection",
            )
            missing = dict(request)
            del missing["operation"]
            check("access-request", missing, False, op + " missing operation")
        for value in ("", "/bad", "a\\b", "CON", "a\u0000b"):
            check(
                "access-request",
                {**requests[1], "name": value},
                True,
                "raw negative name",
            )
        for key, value in (
            ("max_bytes", -1),
            ("max_bytes", True),
            ("max_entries", 2),
            ("max_symlink_hops", 41),
            ("max_symlink_hops", 0),
            ("lifetime_generation", 0),
            ("profile", "invented/v0"),
        ):
            check(
                "access-request",
                {**requests[1], key: value},
                False,
                "request invalid " + key,
            )
        for index, key in (
            (1, "max_bytes"),
            (3, "max_entries"),
            (5, "right_generation"),
        ):
            value = dict(requests[index])
            del value[key]
            check("access-request", value, False, "missing " + key)

        for name in ("a", "dir/file.txt", "caf\u00e9", "cafe\u0301", "file-name"):
            check("root-relative-name", name, True, "admitted " + name)
        for name in (
            "",
            "/a",
            "a/",
            "a//b",
            "a\\b",
            "a\u0000b",
            "a:stream",
            ".",
            "..",
            "a/../b",
            "a/./b",
            "CON",
            "nul.txt",
            "LPT1",
            "COM¹.txt",
            "a/NuL.x",
            "file.",
            "file ",
        ):
            check(
                "root-relative-name",
                name,
                False,
                "structural name refusal " + repr(name),
            )
        for name in ("CON", "file.", "a\\b", "file ", "caf\u00e9"):
            check("observed-name", name, True, "observed non-admitted name")
        for name in ("", ".", "..", "a/b", "a\u0000b"):
            check("observed-name", name, False, "invalid observed entry")

        identity = {"kind": "unix", "device": "1", "inode": "23"}
        handle = {"handle": "handle:result", "lifetime_generation": 1}
        results = [
            {
                "outcome": "accepted",
                "operation": "open_root",
                **handle,
                "identity": identity,
            },
            {
                "outcome": "accepted",
                "operation": "open_read",
                **handle,
                "byte_length": 5,
            },
            {
                "outcome": "accepted",
                "operation": "create_exclusive",
                **handle,
                "mutation": "created",
            },
            {
                "outcome": "accepted",
                "operation": "read_dir",
                "entries": [{"name": "CON", "kind": "symlink"}],
            },
            {"outcome": "accepted", "operation": "stat", "identity": identity},
            {"outcome": "accepted", "operation": "same_object", "same_object": False},
        ]
        for result in results:
            op = result["operation"]
            check("access-result", result, True, op + " result")
            check(
                "access-result",
                {"outcome": "accepted", "operation": op},
                False,
                op + " missing payload",
            )
            check(
                "access-result",
                {**result, "error": {"category": "io_error"}},
                False,
                op + " success with error",
            )
        for reason in (
            "escape",
            "link_refused",
            "reparse_refused",
            "special_file",
            "cross_device",
            "hop_limit",
        ):
            check(
                "access-result",
                {
                    "outcome": "refused",
                    "operation": "open_read",
                    "error": {"category": "policy_denied", "reason": reason},
                },
                True,
                "policy " + reason,
            )
        for category in (
            "invalid_name",
            "unsupported_capability",
            "not_found",
            "already_exists",
            "wrong_type",
            "bound_exceeded",
            "io_error",
            "unknown_mutation_outcome",
        ):
            result = {
                "outcome": "refused",
                "operation": "create_exclusive",
                "error": {"category": category},
            }
            check("access-result", result, True, "error " + category)
            check(
                "access-result",
                {**result, "error": {"category": category, "reason": "escape"}},
                False,
                "reason on " + category,
            )
        for error in (
            {"category": "policy_denied"},
            {"category": "policy_denied", "reason": "ads_ambiguity"},
            {"category": "io_error", "message": "/outside/path"},
            {"category": "invented"},
        ):
            check(
                "access-result",
                {"outcome": "refused", "operation": "open_read", "error": error},
                False,
                "closed error vocabulary",
            )
        for op in ("stat", "same_object"):
            for category in ("io_error", "unsupported_capability"):
                check(
                    "access-result",
                    {
                        "outcome": "refused",
                        "operation": op,
                        "error": {"category": category},
                    },
                    True,
                    "held-handle refusal " + category,
                )
            for category in (
                "invalid_name",
                "bound_exceeded",
                "already_exists",
                "unknown_mutation_outcome",
            ):
                check(
                    "access-result",
                    {
                        "outcome": "refused",
                        "operation": op,
                        "error": {"category": category},
                    },
                    False,
                    "impossible held-handle error",
                )
        windows_identity = {
            "kind": "windows",
            "volume_serial": "000000000000000A",
            "file_id_128": "0" * 32,
        }
        check(
            "access-result",
            {**results[4], "identity": windows_identity},
            True,
            "full-width Windows identity",
        )
        check(
            "access-result",
            {**results[4], "identity": {**windows_identity, "volume_serial": "A"}},
            False,
            "noncanonical Windows serial",
        )
        for bad_identity in (
            {**identity, "inode": "01"},
            {**identity, "inode": 23},
            {"kind": "windows", "volume_serial": "1", "file_id_128": "short"},
        ):
            check(
                "access-result",
                {**results[4], "identity": bad_identity},
                False,
                "identity precision",
            )

        cell = {
            "os": "linux",
            "arch": "arm64",
            "filesystem": "ext4",
            "backend": "linux-openat-walk",
            "operation": "open_read",
            "profile": "no-links/v0",
            "observation_point": "final_open",
            "adversary_level": "stable_tree",
            "enforcement": "manual_stepwise",
            "kernel_mechanism": "openat-directory-nofollow",
            "evidence_refs": ["evidence:fixture"],
            "no_xdev": False,
        }
        report = {
            "capabilities": ["contract: filesystem-access/v0"],
            "report_id": "fixture",
            "cells": [cell],
        }
        check("capability-report", report, True, "manual qualified shape")
        for change in (
            {"adversary_level": "concurrent_rename_resistant"},
            {"enforcement": "kernel_atomic"},
            {"os": "windows"},
            {"evidence_refs": []},
            {"operation": "stat"},
        ):
            check(
                "capability-report",
                {**report, "cells": [{**cell, **change}]},
                False,
                "invalid claim " + repr(change),
            )
        atomic = {
            **cell,
            "backend": "linux-openat2",
            "enforcement": "kernel_atomic",
            "adversary_level": "concurrent_rename_resistant",
            "kernel_mechanism": "openat2-beneath",
        }
        check(
            "capability-report",
            {**report, "cells": [atomic]},
            True,
            "atomic final-open shape",
        )
        check(
            "capability-report",
            {**report, "cells": [{**atomic, "operation": "create_exclusive"}]},
            True,
            "atomic create shape",
        )
        for operation, point in (
            ("create_exclusive", "parent_admission"),
            ("read_dir", "directory_enumeration"),
            ("stat", "held_handle_stat"),
            ("same_object", "identity_comparison"),
            ("open_root", "root_open"),
        ):
            check(
                "capability-report",
                {
                    **report,
                    "cells": [
                        {**atomic, "operation": operation, "observation_point": point}
                    ],
                },
                False,
                "atomic backend cannot qualify " + operation + " at " + point,
            )
        check(
            "capability-report",
            {
                **report,
                "cells": [
                    {
                        **cell,
                        "operation": "create_exclusive",
                        "observation_point": "identity_comparison",
                    }
                ],
            },
            False,
            "create observation mismatch",
        )
        for key in cell:
            changed = dict(cell)
            del changed[key]
            if key != "no_xdev":
                check(
                    "capability-report",
                    {**report, "cells": [changed]},
                    False,
                    "claim missing " + key,
                )
        corpus = json.loads((FAMILY / "cases.json").read_text(encoding="utf-8"))
        check("cases", corpus, True, "published recipe corpus")
        check("cases", {**corpus, "cases": []}, False, "empty recipe corpus")
        for case in corpus["cases"]:
            if case["operation"] in ("open_root", "stat", "same_object"):
                for change in ("mismatch", "duplicate", "missing"):
                    bad_case = copy.deepcopy(case)
                    if change == "mismatch":
                        bad_case["operation"] = "read_dir"
                    elif change == "duplicate":
                        bad_case["request"] = {"no_xdev": True}
                    else:
                        del bad_case["access_request"]
                    check(
                        "cases",
                        {**corpus, "cases": [bad_case]},
                        False,
                        "root/held request source " + change,
                    )
        root_case = next(c for c in corpus["cases"] if c["operation"] == "open_root")
        for key, invalid in (
            ("ref", "../root"),
            ("path", "../outside"),
            ("host_path", "/outside"),
        ):
            bad_case = copy.deepcopy(root_case)
            bad_case["runtime"]["root_bindings"][0][key] = invalid
            check(
                "cases",
                {**corpus, "cases": [bad_case]},
                False,
                "invalid root binding " + key,
            )
        path_case = next(c for c in corpus["cases"] if c["operation"] == "open_read")
        for guarantee in (
            {"no_xdev": True},
            {"adversary": "concurrent_rename_resistant"},
        ):
            bad_case = copy.deepcopy(path_case)
            bad_case["request"] = {}
            bad_case["access_request"] = {**requests[1], "capabilities": guarantee}
            check(
                "cases",
                {**corpus, "cases": [bad_case]},
                False,
                "embedded path request cannot weaken guarantee",
            )
        bad_case = copy.deepcopy(
            next(c for c in corpus["cases"] if c["operation"] == "stat")
        )
        bad_case["operation"] = "open_root"
        check(
            "cases",
            {**corpus, "cases": [bad_case]},
            False,
            "root/held operation mismatch",
        )
        bad = copy.deepcopy(corpus)
        bad["cases"][0]["recipe"][0]["host_path"] = "/outside"
        check("cases", bad, False, "recipe host-path injection")
        for path in ("a/../escape", "a//b", "a\\b", "/outside", "a/."):
            bad = copy.deepcopy(corpus)
            bad["cases"][0]["recipe"][0]["path"] = path
            check("cases", bad, False, "unsafe recipe location")
        for extra in ({"category": "io_error"}, {"reason": "escape"}):
            bad = copy.deepcopy(corpus)
            bad["cases"][0]["expected"].update(extra)
            check("cases", bad, False, "success with expected error")
    require(not failures, "schema controls failed:\n" + "\n".join(failures))
    print(f"[ok] filesystem-access schema controls: {count}")
    return count


if __name__ == "__main__":
    run_schema_controls()
