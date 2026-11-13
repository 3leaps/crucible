#!/usr/bin/env python3
"""Availability-only native Unix probes for filesystem-access/v0.

These checks exercise primitive open behavior in isolated fixtures.  They do
not implement a resolver and do not qualify an access profile, race guarantee,
or production backend.  Profile labels on leaf checks identify the contract
contexts that need this primitive; they do not change the native operation.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import platform
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class ProbeFailure(RuntimeError):
    """A native behavior differed from the availability control."""


_DIRECTORY_FLAG_NAMES = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")
_LEAF_FLAG_NAMES = ("O_NONBLOCK", "O_NOFOLLOW", "O_CLOEXEC")
_DIRECTORY_REFUSAL_ERRNOS = {errno.ENOTDIR, errno.ELOOP}
_WORKER_TIMEOUT_SECONDS = 3


def _required_flags(names: tuple[str, ...]) -> int:
    """Return flags after confirming this host exposes every requested flag."""

    flags = 0
    for name in names:
        flags |= getattr(os, name)
    return flags


def _availability_skip_reason() -> str | None:
    if os.name != "posix":
        return f"requires POSIX Unix primitives; host os.name={os.name!r}"
    missing = [
        name
        for name in (*_DIRECTORY_FLAG_NAMES, *_LEAF_FLAG_NAMES)
        if not hasattr(os, name)
    ]
    if missing:
        return "missing required os flags: " + ", ".join(sorted(set(missing)))
    if not hasattr(os, "mkfifo"):
        return "os.mkfifo is unavailable"
    return None


def _emit(status: str, **details: Any) -> None:
    print(json.dumps({"status": status, **details}, sort_keys=True))


def _worker_directory(path: Path, root: Path | None, name: str | None) -> int:
    """Attempt the directory-only open under test and emit one JSON result."""

    directory_flags = os.O_RDONLY | _required_flags(_DIRECTORY_FLAG_NAMES)
    root_fd: int | None = None
    target_fd: int | None = None
    try:
        if root is None:
            target_fd = os.open(path, directory_flags)
        else:
            root_fd = os.open(root, directory_flags)
            target_fd = os.open(name or "", directory_flags, dir_fd=root_fd)
        mode = os.fstat(target_fd).st_mode
        _emit("opened", directory=stat.S_ISDIR(mode))
    except OSError as error:
        _emit("refused", errno=error.errno)
    finally:
        if target_fd is not None:
            os.close(target_fd)
        if root_fd is not None:
            os.close(root_fd)
    return 0


def _worker_leaf(path: Path) -> int:
    """Open a leaf without blocking, then report its held descriptor type."""

    leaf_flags = os.O_RDONLY | _required_flags(_LEAF_FLAG_NAMES)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, leaf_flags)
        mode = os.fstat(descriptor).st_mode
        if stat.S_ISREG(mode):
            _emit("accepted_regular")
        elif stat.S_ISFIFO(mode):
            _emit("rejected_nonregular", kind="fifo")
        else:
            _emit("rejected_nonregular", kind="other")
    except OSError as error:
        _emit("native_error", errno=error.errno)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return 0


def _worker_main(arguments: argparse.Namespace) -> int:
    if arguments.worker == "directory":
        return _worker_directory(
            Path(arguments.path) if arguments.path is not None else Path("."),
            Path(arguments.root) if arguments.root is not None else None,
            arguments.name,
        )
    if arguments.worker == "leaf":
        if arguments.path is None:
            raise ProbeFailure("leaf worker requires --path")
        return _worker_leaf(Path(arguments.path))
    raise ProbeFailure(f"unknown worker {arguments.worker!r}")


def _run_worker(*arguments: str) -> dict[str, Any]:
    """Run one potentially blocking primitive in a bounded child process."""

    command = [sys.executable, str(Path(__file__).resolve()), "--worker", *arguments]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
        )
    except subprocess.TimeoutExpired as error:
        raise ProbeFailure(
            f"worker timed out after {_WORKER_TIMEOUT_SECONDS}s: {arguments!r}"
        ) from error
    if completed.returncode != 0:
        raise ProbeFailure(
            "worker exited unexpectedly "
            f"({completed.returncode}): stdout={completed.stdout!r} "
            f"stderr={completed.stderr!r}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ProbeFailure(
            f"worker returned non-JSON output: {completed.stdout!r}; "
            f"stderr={completed.stderr!r}"
        ) from error
    if not isinstance(result, dict) or not isinstance(result.get("status"), str):
        raise ProbeFailure(f"worker returned invalid result: {result!r}")
    return result


def _require_directory(path: Path, *, parent: int | None = None) -> None:
    """Check a positive directory-only control without spawning a worker."""

    flags = os.O_RDONLY | _required_flags(_DIRECTORY_FLAG_NAMES)
    if parent is None:
        descriptor = os.open(path, flags)
    else:
        descriptor = os.open(path.name, flags, dir_fd=parent)
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ProbeFailure(f"directory control opened a non-directory: {path}")
    finally:
        os.close(descriptor)


def _require_directory_refusal(label: str, *arguments: str) -> None:
    result = _run_worker("directory", *arguments)
    if result.get("status") != "refused":
        raise ProbeFailure(f"{label}: expected directory-open refusal, got {result!r}")
    if result.get("errno") not in _DIRECTORY_REFUSAL_ERRNOS:
        raise ProbeFailure(f"{label}: unexpected native refusal {result!r}")


def _require_leaf(label: str, path: Path, expected_status: str) -> None:
    result = _run_worker("leaf", "--path", str(path))
    if result.get("status") != expected_status:
        raise ProbeFailure(f"{label}: expected {expected_status}, got {result!r}")
    if expected_status == "rejected_nonregular" and result.get("kind") != "fifo":
        raise ProbeFailure(f"{label}: expected held FIFO descriptor, got {result!r}")


def run_native_probes() -> int:
    """Run native availability controls and return the completed probe count.

    Unsupported hosts print an explicit non-qualification skip and return zero.
    Unexpected native results and timeouts raise ``ProbeFailure``.
    """

    skip_reason = _availability_skip_reason()
    if skip_reason is not None:
        print(f"SKIP: native Unix probes not qualified: {skip_reason}")
        return 0

    probes = 0
    with tempfile.TemporaryDirectory(prefix="filesystem-access-native-") as work:
        workspace = Path(work)
        root = workspace / "root"
        root.mkdir()
        directory = root / "directory"
        directory.mkdir()
        regular = root / "regular"
        regular.write_bytes(b"regular control\n")
        fifo = root / "fifo"
        os.mkfifo(fifo)
        directory_link = root / "directory-link"
        os.symlink(directory.name, directory_link)

        _require_directory(root)
        probes += 1
        root_fd = os.open(root, os.O_RDONLY | _required_flags(_DIRECTORY_FLAG_NAMES))
        try:
            _require_directory(directory, parent=root_fd)
        finally:
            os.close(root_fd)
        probes += 1

        for label, arguments in (
            ("root FIFO", ("--path", str(fifo))),
            ("intermediate FIFO", ("--root", str(root), "--name", fifo.name)),
            ("root regular", ("--path", str(regular))),
            (
                "intermediate regular",
                ("--root", str(root), "--name", regular.name),
            ),
            ("root symlink", ("--path", str(directory_link))),
            (
                "intermediate symlink",
                ("--root", str(root), "--name", directory_link.name),
            ),
        ):
            _require_directory_refusal(label, *arguments)
            probes += 1

        for profile in ("containment/v0", "no-links/v0"):
            _require_leaf(f"{profile} regular leaf", regular, "accepted_regular")
            probes += 1
            _require_leaf(f"{profile} FIFO leaf", fifo, "rejected_nonregular")
            probes += 1

    print(
        f"OK: {probes} native Unix availability probes passed on "
        f"{platform.system()} {platform.release()}"
    )
    return probes


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("directory", "leaf"))
    parser.add_argument("--path")
    parser.add_argument("--root")
    parser.add_argument("--name")
    return parser.parse_args()


def main() -> int:
    arguments = _parse_arguments()
    if arguments.worker is not None:
        return _worker_main(arguments)
    try:
        run_native_probes()
    except ProbeFailure as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
