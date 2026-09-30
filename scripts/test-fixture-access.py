#!/usr/bin/env python3
"""Deny/restore read access to disposable permission-control fixtures."""

import os
import subprocess
import sys
from pathlib import Path


def windows_sid():
    sid = subprocess.check_output(
        [
            "pwsh",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value",
        ],
        text=True,
    ).strip()
    if not sid.startswith("S-1-") or not all(c in "S0123456789-" for c in sid):
        raise ValueError("could not resolve the current Windows SID")
    return f"*{sid}"


def set_access(path, deny):
    # These are freshly created, disposable fixtures, never production paths.
    if path.name not in {"unreadable.json", "unreadable-dir"}:
        raise ValueError("only named unreadable test fixtures may be changed")
    if path.is_symlink():
        raise ValueError("permission fixtures must not be symlinks")
    if os.name == "nt":
        sid = windows_sid()
        args = ["/deny", f"{sid}:(RX)"] if deny else ["/remove:d", sid]
        targets = [path]
        if path.name == "unreadable-dir":
            child = path / "ok.json"
            if child.is_symlink():
                raise ValueError("permission fixture member must not be a symlink")
            # Windows can still enumerate a denied directory. Deny the known
            # disposable record too so a directory-target validator cannot read it.
            targets.insert(0, child)
        # Restore directory access before touching its member's ACL.
        if not deny:
            targets.reverse()
        try:
            for target in targets:
                subprocess.run(["icacls.exe", str(target), *args], check=True)
        except subprocess.CalledProcessError:
            if deny:
                for target in reversed(targets):
                    subprocess.run(
                        ["icacls.exe", str(target), "/remove:d", sid], check=False
                    )
            raise
    else:
        os.chmod(path, 0 if deny else (0o700 if path.is_dir() else 0o600))


def assert_unreadable(path):
    try:
        if path.is_dir():
            # Test inaccessible directory contents, not an OS-specific promise
            # that directory-name enumeration is denied.
            with (path / "ok.json").open("rb") as stream:
                stream.read(1)
        else:
            with path.open("rb") as stream:
                stream.read(1)
    except PermissionError:
        return
    raise ValueError("fixture setup did not actually deny read access")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in {"deny", "restore"}:
        print("usage: test-fixture-access.py deny|restore PATH", file=sys.stderr)
        return 2
    path = Path(sys.argv[2]).absolute()
    try:
        set_access(path, sys.argv[1] == "deny")
        if sys.argv[1] == "deny":
            try:
                assert_unreadable(path)
            except Exception:
                set_access(path, False)
                raise
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
