#!/usr/bin/env python3
"""Fail-closed native platform, Goneat identity, and aggregate checks for CI."""

import os
import platform
import re
import struct
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from pathlib import Path


def normalize_arch(value):
    return {
        "x64": "amd64",
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(value.lower(), value.lower())


def require_identity(expected_os, expected_arch, actual_os, actual_arch, bits):
    if expected_os not in {"linux", "darwin", "windows"}:
        raise ValueError("unknown expected operating system")
    if expected_arch not in {"amd64", "arm64"}:
        raise ValueError("unknown expected architecture")
    if (actual_os.lower(), normalize_arch(actual_arch), bits) != (
        expected_os,
        expected_arch,
        64,
    ):
        raise ValueError(
            f"expected native {expected_os}/{expected_arch}, "
            f"got {actual_os}/{actual_arch} ({bits}-bit)"
        )


def require_results(linux, native):
    if linux != "success" or native != "success":
        raise ValueError(f"all five platforms required: linux={linux}, native={native}")


def require_windows_python(arch, python_platform):
    expected = {"amd64": "win-amd64", "arm64": "win-arm64"}[arch]
    if python_platform != expected:
        raise ValueError(f"expected native Python {expected}, got {python_platform}")


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


def verify(expected_os, expected_arch):
    require_identity(
        expected_os,
        expected_arch,
        platform.system(),
        platform.machine(),
        struct.calcsize("P") * 8,
    )
    runner_arch = os.environ.get("RUNNER_ARCH")
    if runner_arch and normalize_arch(runner_arch) != expected_arch:
        raise ValueError(f"runner metadata disagrees: RUNNER_ARCH={runner_arch}")
    if expected_os == "windows":
        require_windows_python(expected_arch, sysconfig.get_platform())
    pins = Path("Makefile").read_text(encoding="utf-8")
    match = re.search(r"^GONEAT_VERSION\s*\?=\s*(v[0-9.]+)\s*$", pins, re.M)
    if not match:
        raise ValueError("missing exact Makefile Goneat pin")
    output = subprocess.check_output(["goneat", "version"], text=True)
    print(output, end="")
    if not output.splitlines() or output.splitlines()[0] != f"goneat {match[1]}":
        raise ValueError("Goneat does not match the repository pin")
    expected = f"Platform: {expected_os}/{expected_arch}"
    if expected not in output.splitlines():
        raise ValueError(f"Goneat must execute natively: missing {expected}")
    print(f"[ok] native {expected_os}/{expected_arch} and exact Goneat pin")


class IdentityTests(unittest.TestCase):
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
                            list(path.iterdir())
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

    def test_supported_native_hosts(self):
        for host in (
            ("linux", "amd64", "Linux", "x86_64"),
            ("linux", "arm64", "Linux", "aarch64"),
            ("darwin", "arm64", "Darwin", "arm64"),
            ("windows", "amd64", "Windows", "AMD64"),
            ("windows", "arm64", "Windows", "ARM64"),
        ):
            with self.subTest(host=host):
                require_identity(*host, 64)

    def test_emulated_or_wrong_hosts_refused(self):
        for host in (
            ("windows", "arm64", "Windows", "AMD64", 64),
            ("linux", "amd64", "Linux", "aarch64", 64),
            ("darwin", "arm64", "Linux", "arm64", 64),
            ("windows", "amd64", "Windows", "AMD64", 32),
            ("linux", "arm64", "Linux", "unknown", 64),
        ):
            with self.subTest(host=host), self.assertRaises(ValueError):
                require_identity(*host)

    def test_all_platform_results_required(self):
        require_results("success", "success")
        for status in ("failure", "cancelled", "skipped", "", "unknown"):
            for results in ((status, "success"), ("success", status)):
                with self.subTest(results=results), self.assertRaises(ValueError):
                    require_results(*results)

    def test_windows_interpreter_architecture(self):
        require_windows_python("amd64", "win-amd64")
        require_windows_python("arm64", "win-arm64")
        for arch, actual in (("arm64", "win-amd64"), ("amd64", "win32")):
            with self.subTest(arch=arch), self.assertRaises(ValueError):
                require_windows_python(arch, actual)


def main():
    if sys.argv[1:] == ["self-test"]:
        result = unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromTestCase(IdentityTests)
        )
        return 0 if result.wasSuccessful() else 1
    if len(sys.argv) != 4 or sys.argv[1] not in {"verify", "gate"}:
        print(
            "usage: ci-platforms.py verify OS ARCH | gate LINUX NATIVE | self-test",
            file=sys.stderr,
        )
        return 2
    try:
        if sys.argv[1] == "gate":
            require_results(sys.argv[2], sys.argv[3])
        else:
            verify(sys.argv[2], sys.argv[3])
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
