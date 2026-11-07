#!/usr/bin/env python3
"""Tier 1 repository surface hygiene check for generic local filesystem paths.

Scans tracked files (or explicit paths) for generic host-local path shapes:
  - macOS user home prefix
  - Linux user home prefix
  - Windows user home prefix
  - host devsecops home prefix

Fails closed on NUL bytes in tracked files and uses line-level allowlisting so
that new local-path occurrences inside files with existing documented examples
are still caught.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

_MAC_PREFIX = "/" + "Users/"
_LIN_PREFIX = "/" + "home/"
_WIN_USERS = "Users"
_DEVSECOPS_PREFIX = "~/" + "devsecops"

LOCAL_PATH_RE = re.compile(
    r"(?P<macos>(?<![A-Za-z0-9_.-])" + _MAC_PREFIX + r"[A-Za-z0-9_.][A-Za-z0-9_.$-]*)"
    r"|(?P<linux>(?<![A-Za-z0-9_.-])" + _LIN_PREFIX + r"[A-Za-z0-9_.][A-Za-z0-9_.$-]*)"
    r"|(?P<windows>\b[A-Za-z]:(?:\\|/)+"
    + _WIN_USERS
    + r"(?:\\|/)+[A-Za-z0-9_.~-][A-Za-z0-9_.$~-]*)"
    r"|(?P<devsecops>" + _DEVSECOPS_PREFIX + r"\b)"
)

# Line-level allowlist: only lines containing one of the listed snippets in the
# named file are exempted; all other lines in that file are still scanned.
ALLOWLISTED_LINE_SNIPPETS: dict[str, tuple[str, ...]] = {
    "docs/coding/go.md": ('configPath := "' + _LIN_PREFIX + 'user/.config/app.yaml"',),
    "docs/knowledge/cicd/github-actions/container-non-root-pitfalls.md": (
        "| `" + _LIN_PREFIX + "runner`",
        "references `$HOME` or hardcodes paths under `/root`, `"
        + _LIN_PREFIX
        + "user`, or `/opt`",
    ),
    "docs/knowledge/cicd/github-actions/windows-runners.md": (
        "on a different drive (e.g., `C:\\" + _WIN_USERS + "\\...`)",
        "Expected: C:\\" + _WIN_USERS + "\\me\\bin\\tool.exe",
        "Actual:   C:\\" + _WIN_USERS + "\\me\\bin\\tool",
    ),
    "docs/knowledge/toolchains/typescript/windows-arm64-gaps.md": (
        'expect(result).toBe("' + _LIN_PREFIX + 'user/project/docs/guide.md");',
        'expect(result).toBe(resolve("'
        + _LIN_PREFIX
        + 'user/project", "docs", "guide.md"));',
    ),
    "scripts/test-durable-queue-controls.sh": (
        "(password|secret|bearer |/users/|" + _LIN_PREFIX + "|c:\\\\users)",
    ),
    "scripts/test-durable-record-controls.sh": (
        "(" + _MAC_PREFIX + "|" + _LIN_PREFIX + "|[A-Za-z]:\\\\|AGE-SECRET-KEY-",
    ),
    "scripts/test-release-env.sh": (
        '[ "$*" = ". -read '
        + _MAC_PREFIX
        + 'releaser NFSHomeDirectory" ] && echo "NFSHomeDirectory: $FAKE_ACCOUNT_HOME"',
    ),
    "scripts/test-segmented-snapshot-controls.py": (
        '(pathlib.PureWindowsPath, "C:/'
        + _WIN_USERS
        + '/RUNNER~1/AppData/Local/Temp")',
        '"D:/'
        + _WIN_USERS
        + '/RUNNER~1/AppData/Local/Temp/snapshot-schema-test/node-0.schema.json"',
        '"C:/'
        + _WIN_USERS
        + '/runneradmin/AppData/Local/Temp/snapshot-schema-test/node-0.schema.json"',
    ),
}


def tracked_files(root: pathlib.Path) -> list[pathlib.Path]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    entries = [p for p in proc.stdout.decode("utf-8").split("\0") if p]
    return [root / rel for rel in sorted(entries)]


def is_line_allowlisted(rel_posix: str, line: str) -> bool:
    snippets = ALLOWLISTED_LINE_SNIPPETS.get(rel_posix, ())
    return any(snippet in line for snippet in snippets)


def scan_file(path: pathlib.Path, rel_posix: str) -> list[str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [f"{rel_posix}: could not read file: {exc}"]
    if b"\x00" in raw:
        return [f"{rel_posix}: unexpected NUL byte in tracked file"]
    text = raw.decode("utf-8", errors="replace")
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if is_line_allowlisted(rel_posix, line):
            continue
        match = LOCAL_PATH_RE.search(line)
        if match:
            findings.append(
                f"{rel_posix}:{lineno}: forbidden local path pattern '{match.group(0)}'"
            )
    return findings


def scan_repo(root: pathlib.Path) -> list[str]:
    findings: list[str] = []
    for path in tracked_files(root):
        if not path.is_file():
            continue
        rel_posix = path.relative_to(root).as_posix()
        findings.extend(scan_file(path, rel_posix))
    return findings


def run_self_test() -> None:
    positive_samples = [
        "normal relative path docs/standards/durable-record-v1-contract.md\n",
        "url https://example.com/api/v1/users/list\n",
    ]
    negative_samples = [
        (
            "macos-home",
            "leaked path " + _MAC_PREFIX + "alice/work/project\n",
            _MAC_PREFIX + "alice",
        ),
        (
            "linux-home",
            "leaked path " + _LIN_PREFIX + "bob/work/project\n",
            _LIN_PREFIX + "bob",
        ),
        (
            "windows-home",
            "leaked path C:\\" + _WIN_USERS + "\\carol\\work\\project\n",
            "C:\\" + _WIN_USERS + "\\carol",
        ),
        (
            "devsecops-home",
            "source " + _DEVSECOPS_PREFIX + "/vars/profile.sh\n",
            _DEVSECOPS_PREFIX,
        ),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = pathlib.Path(tmp)
        clean_file = tmp_root / "clean.md"
        clean_file.write_text("".join(positive_samples), encoding="utf-8")
        if scan_file(clean_file, "clean.md"):
            raise SystemExit("error: self-test clean sample unexpectedly failed")

        for label, sample, expected_token in negative_samples:
            bad_file = tmp_root / f"{label}.md"
            bad_file.write_text(sample, encoding="utf-8")
            res = scan_file(bad_file, f"{label}.md")
            if not res or expected_token not in res[0]:
                raise SystemExit(
                    f"error: self-test negative control '{label}' did not fail as expected: {res}"
                )

        # Un-allowlisted line in an allowlisted file path must still be caught.
        mixed_file = tmp_root / "go.md"
        mixed_file.write_text(
            'configPath := "' + _LIN_PREFIX + 'user/.config/app.yaml"\n'
            'otherPath := "' + _MAC_PREFIX + 'alice/secret.yaml"\n',
            encoding="utf-8",
        )
        res_mixed = scan_file(mixed_file, "docs/coding/go.md")
        if len(res_mixed) != 1 or "docs/coding/go.md:2:" not in res_mixed[0]:
            raise SystemExit(
                f"error: self-test line-level allowlist control failed: {res_mixed}"
            )

        # NUL byte in tracked file must fail closed.
        nul_file = tmp_root / "nul.md"
        nul_file.write_bytes(
            ("header\x00" + _MAC_PREFIX + "alice/secret\n").encode("utf-8")
        )
        res_nul = scan_file(nul_file, "nul.md")
        if not res_nul or "unexpected NUL byte" not in res_nul[0]:
            raise SystemExit(f"error: self-test NUL-byte control failed: {res_nul}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run EPR-0002 negative controls before scanning tracked files.",
    )
    args = parser.parse_args()

    if args.self_test:
        run_self_test()

    findings = scan_repo(REPO_ROOT)
    if findings:
        for item in findings:
            sys.stderr.write(f"error: {item}\n")
        return 1

    if args.self_test:
        print("[ok] content-check self-test and tracked-file local-path scan passed")
    else:
        print("[ok] tracked-file local-path scan passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
