#!/usr/bin/env python3
"""Windows path, subprocess decoding and permission-fixture self-tests."""

import ast
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def require_portable_path(path):
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    }
    for part in path.split("/"):
        if (
            not part
            or re.search(r'[<>:"\\|?*\x00-\x1f]', part)
            or part.endswith((".", " "))
            or part.split(".")[0].upper() in reserved
        ):
            raise ValueError(f"path cannot be checked out on Windows: {path}")


class PortabilityTests(unittest.TestCase):
    def test_subprocess_output_decoding(self):
        # Exercise the decoding options at each real text-mode helper call with
        # a child that writes bytes, independent of the host's default locale.
        payload = b"utf8: \xe2\x9c\x9d; malformed: \xff\n"
        with self.assertRaises(UnicodeDecodeError):
            payload.decode("cp1252")
        expected = "utf8: \u271d; malformed: \ufffd\n"
        popen = subprocess.Popen

        def windows_default(*args, **kwargs):
            kwargs.setdefault("encoding", "cp1252")
            return popen(*args, **kwargs)

        sites = 0
        for path in sorted(Path("scripts").glob("test-*.py")):
            if path.name == "test-portability.py":
                continue
            for node in ast.walk(ast.parse(path.read_bytes())):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                    and node.func.attr in {"run", "check_output"}
                ):
                    continue
                options = {k.arg: ast.literal_eval(k.value) for k in node.keywords}
                if options.get("text") is not True:
                    continue
                sites += 1
                # check_output uses the same decoder and implies check=True.
                if node.func.attr == "check_output":
                    options.update(capture_output=True, check=True)
                for code in (0, 2):
                    with self.subTest(site=f"{path}:{node.lineno}", exit=code):
                        command = [
                            sys.executable,
                            "-c",
                            "import os, sys; "
                            f"os.write(1, {payload!r}); os.write(2, {payload!r}); "
                            f"sys.exit({code})",
                        ]
                        with patch("subprocess.Popen", side_effect=windows_default):
                            try:
                                result = subprocess.run(command, **options)
                            except subprocess.CalledProcessError as error:
                                self.assertTrue(options.get("check"))
                                self.assertEqual(code, 2)
                                result = error
                        self.assertEqual(result.returncode, code)
                        self.assertEqual(result.stdout, expected)
                        self.assertEqual(result.stderr, expected)
        self.assertGreater(sites, 0, "no text-mode helper calls exercised")

    def test_windows_acl_restore_and_rollback_order(self):
        helper = runpy.run_path("scripts/test-fixture-access.py")["set_access"]
        with tempfile.TemporaryDirectory(prefix="crucible-acl-order-") as work:
            directory = Path(work) / "unreadable-dir"
            directory.mkdir()
            child = directory / "ok.json"
            child.write_bytes(b"fixture\n")
            calls = []

            def run(args, check):
                calls.append(args)
                if len(calls) == 2 and args[2] == "/deny":
                    raise subprocess.CalledProcessError(5, args)

            mocks = {
                "os": SimpleNamespace(name="nt"),
                "windows_sid": lambda: "*S-1-5-21-1",
                "subprocess": SimpleNamespace(
                    run=run, CalledProcessError=subprocess.CalledProcessError
                ),
            }
            with patch.dict(helper.__globals__, mocks):
                helper(directory, False)
                self.assertEqual(
                    [call[1] for call in calls], [str(directory), str(child)]
                )
                calls.clear()
                with self.assertRaises(subprocess.CalledProcessError):
                    helper(directory, True)
                self.assertEqual(
                    [call[1] for call in calls],
                    [str(child), str(directory), str(directory), str(child)],
                )
                self.assertEqual(
                    [call[3] for call in calls[:2]], ["*S-1-5-21-1:(RD)"] * 2
                )
                self.assertEqual([call[2] for call in calls[2:]], ["/remove:d"] * 2)

    def test_permission_fixture_setup_and_restore(self):
        helper = "scripts/test-fixture-access.py"
        with tempfile.TemporaryDirectory(prefix="crucible-permissions-") as work:
            file = Path(work) / "unreadable.json"
            file.write_bytes(b"fixture\n")
            directory = Path(work) / "unreadable-dir"
            directory.mkdir()
            (directory / "ok.json").write_bytes(b"fixture\n")
            for path in (file, directory):
                try:
                    subprocess.run(
                        [sys.executable, helper, "deny", str(path)], check=True
                    )
                    with self.assertRaises(PermissionError):
                        if path == directory:
                            (path / "ok.json").read_bytes()
                        else:
                            path.read_bytes()
                finally:
                    subprocess.run(
                        [sys.executable, helper, "restore", str(path)], check=True
                    )
            self.assertEqual(file.read_bytes(), b"fixture\n")
            self.assertEqual((directory / "ok.json").read_bytes(), b"fixture\n")

    def test_tracked_paths_are_windows_portable(self):
        paths = subprocess.check_output(["git", "ls-files", "-z"], text=True)
        for path in paths.split("\0"):
            if path:
                with self.subTest(path=path):
                    require_portable_path(path)

    def test_nonportable_paths_refused(self):
        require_portable_path("schemas/service-job/sj-admit-1.json")
        for path in ("fixtures/msg:1.json", "fixtures/CON.json", "a/b.", "a/b "):
            with self.subTest(path=path), self.assertRaises(ValueError):
                require_portable_path(path)


if __name__ == "__main__":
    result = unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(PortabilityTests)
    )
    sys.exit(0 if result.wasSuccessful() else 1)
