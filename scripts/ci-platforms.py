#!/usr/bin/env python3
"""Fail-closed native platform, Goneat identity, and aggregate checks for CI."""

import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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


def repository_version():
    pins = Path("Makefile").read_text(encoding="utf-8")
    match = re.search(r"^GONEAT_VERSION\s*\?=\s*(v[0-9.]+)\s*$", pins, re.M)
    if not match:
        raise ValueError("missing exact Makefile Goneat pin")
    return match[1]


def source_pins():
    pins = json.loads(Path(".github/goneat-source.json").read_text(encoding="utf-8"))
    if pins["version"] != repository_version():
        raise ValueError("source-build pin disagrees with Makefile")
    return pins


def require_acquisition(route, os_name, arch):
    if route not in {"release", "source"}:
        raise ValueError("unknown Goneat acquisition route")
    if route == "source" and (os_name, arch) != ("windows", "arm64"):
        raise ValueError("source acquisition is only selected for Windows arm64")


def require_source_download(metadata, pins):
    expected = {
        "Path": pins["module"],
        "Version": pins["version"],
        "Sum": pins["sum"],
        "GoModSum": pins["go_mod_sum"],
    }
    if metadata.get("Error") or any(metadata.get(k) != v for k, v in expected.items()):
        raise ValueError("downloaded Go source does not match committed module pins")


def require_source_build(metadata, pins):
    lines = metadata.splitlines()
    if not lines or not lines[0].endswith(": " + pins["compiler"]):
        raise ValueError("source executable compiler does not match the pin")
    records = [line.split() for line in lines[1:]]
    required = [
        ["path", pins["module"]],
        ["mod", pins["module"], pins["version"], pins["sum"]],
        ["build", "GOOS=windows"],
        ["build", "GOARCH=arm64"],
        ["build", "CGO_ENABLED=0"],
    ]
    if any(record not in records for record in required):
        raise ValueError("source executable lacks exact native module/build identity")


def install_source():
    if os.environ.get("GONEAT_ACQUISITION") != "source":
        raise ValueError("source acquisition must be explicitly selected")
    require_identity(
        "windows",
        "arm64",
        platform.system(),
        platform.machine(),
        struct.calcsize("P") * 8,
    )
    require_windows_python("arm64", sysconfig.get_platform())
    pins = source_pins()
    env = os.environ.copy()
    # Explicit authenticated Go checksum-database route; no private/direct bypass,
    # cross compilation, toolchain auto-download or alternate acquisition fallback.
    env.update(
        GOPROXY="https://proxy.golang.org",
        GOSUMDB="sum.golang.org",
        GOPRIVATE="",
        GONOPROXY="",
        GONOSUMDB="",
        GOFLAGS="",
        GOTOOLCHAIN="local",
        GOOS="windows",
        GOARCH="arm64",
        CGO_ENABLED="0",
    )
    if Path(env.get("GOBIN", "")).resolve() != Path("bin").resolve():
        raise ValueError("source install must use repo-local bin")
    actual = subprocess.check_output(
        ["go", "env", "GOVERSION", "GOHOSTOS", "GOHOSTARCH"], text=True, env=env
    ).splitlines()
    if actual != [pins["compiler"], "windows", "arm64"]:
        raise ValueError(f"unexpected source-build compiler/host: {actual}")
    module = f"{pins['module']}@{pins['version']}"
    metadata = json.loads(
        subprocess.check_output(
            ["go", "mod", "download", "-json", module], text=True, env=env
        )
    )
    require_source_download(metadata, pins)
    print(
        f"[ok] source module/checksums {module}; compiler {pins['compiler']}",
        flush=True,
    )
    subprocess.run(["go", "install", module], check=True, env=env)
    binary = str(Path("bin/goneat.exe").resolve())
    metadata = subprocess.check_output(
        ["go", "version", "-m", binary], text=True, env=env
    )
    print(metadata, end="")
    require_source_build(metadata, pins)


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
    version = repository_version()
    route = os.environ.get("GONEAT_ACQUISITION", "release")
    require_acquisition(route, expected_os, expected_arch)
    output = subprocess.check_output(["goneat", "version"], text=True)
    print(output, end="")
    if route == "source":
        pins = source_pins()
        if (
            not output.startswith("goneat dev\n")
            or f"Module: {version}" not in output.splitlines()
        ):
            raise ValueError(
                "source build must retain truthful dev banner/module identity"
            )
        binary = shutil.which("goneat")
        if not binary:
            raise ValueError("source executable not found")
        metadata = subprocess.check_output(["go", "version", "-m", binary], text=True)
        print(metadata, end="")
        require_source_build(metadata, pins)
    elif not output.splitlines() or output.splitlines()[0] != f"goneat {version}":
        raise ValueError("Goneat does not match the repository pin")
    expected = f"Platform: {expected_os}/{expected_arch}"
    if expected not in output.splitlines():
        raise ValueError(f"Goneat must execute natively: missing {expected}")
    print(f"[ok] native {expected_os}/{expected_arch} and exact Goneat pin")


class IdentityTests(unittest.TestCase):
    def test_source_route_is_explicit_and_bounded(self):
        with patch.dict(os.environ, {"GONEAT_ACQUISITION": "release"}):
            with self.assertRaises(ValueError):
                install_source()
        require_acquisition("source", "windows", "arm64")
        for route, host, arch in (
            ("fallback", "windows", "arm64"),
            ("source", "windows", "amd64"),
            ("source", "linux", "arm64"),
        ):
            with self.subTest(route=route, host=host), self.assertRaises(ValueError):
                require_acquisition(route, host, arch)

    def test_source_checksums_and_build_metadata(self):
        pins = source_pins()
        download = {
            "Path": pins["module"],
            "Version": pins["version"],
            "Sum": pins["sum"],
            "GoModSum": pins["go_mod_sum"],
        }
        require_source_download(download, pins)
        for key in download:
            with self.subTest(key=key), self.assertRaises(ValueError):
                require_source_download({**download, key: "wrong"}, pins)
        metadata = (
            f"goneat.exe: {pins['compiler']}\n"
            f"\tpath\t{pins['module']}\n"
            f"\tmod\t{pins['module']}\t{pins['version']}\t{pins['sum']}\n"
            "\tbuild\tGOOS=windows\n\tbuild\tGOARCH=arm64\n"
            "\tbuild\tCGO_ENABLED=0\n"
        )
        require_source_build(metadata, pins)
        for old, new in (
            (pins["compiler"], "go1.26.8"),
            (pins["sum"], "h1:wrong"),
            ("GOARCH=arm64", "GOARCH=amd64"),
            ("GOOS=windows", "GOOS=linux"),
        ):
            with self.subTest(old=old), self.assertRaises(ValueError):
                require_source_build(metadata.replace(old, new), pins)

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
    if sys.argv[1:] == ["install-source"]:
        try:
            install_source()
        except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0
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
