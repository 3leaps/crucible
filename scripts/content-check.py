#!/usr/bin/env python3
"""Tier 1 repository surface hygiene check for generic local filesystem paths.

Scans tracked files (or explicit paths) for generic host-local path shapes:
  - /Users/<name>
  - /home/<name>
  - <Drive>:\\Users\\<name> or <Drive>:/Users/<name>
  - ~/devsecops

Contains only generic OS path-shape patterns and an explicit allowlist of
documentation/control files that intentionally illustrate generic OS paths.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

LOCAL_PATH_RE = re.compile(
    r"(?P<macos>(?<![A-Za-z0-9_.-])/Users/[A-Za-z0-9_.$][A-Za-z0-9_.$-]*)"
    r"|(?P<linux>(?<![A-Za-z0-9_.-])/home/[A-Za-z0-9_.$][A-Za-z0-9_.$-]*)"
    r"|(?P<windows>\b[A-Za-z]:(?:\\|/)+Users(?:\\|/)+[A-Za-z0-9_.$~-][A-Za-z0-9_.$~-]*)"
    r"|(?P<devsecops>~/devsecops\b)"
)

# Files that intentionally document generic OS path examples or test local-path
# rejection in control suites.
ALLOWLISTED_PATHS: frozenset[str] = frozenset(
    {
        "docs/coding/go.md",
        "docs/knowledge/cicd/github-actions/container-non-root-pitfalls.md",
        "docs/knowledge/cicd/github-actions/windows-runners.md",
        "docs/knowledge/toolchains/typescript/windows-arm64-gaps.md",
        "scripts/content-check.py",
        "scripts/release-env.sh",
        "scripts/test-durable-queue-controls.sh",
        "scripts/test-durable-record-controls.sh",
        "scripts/test-release-env.sh",
        "scripts/test-segmented-snapshot-controls.py",
    }
)


def tracked_files(root: pathlib.Path) -> list[pathlib.Path]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    entries = [p for p in proc.stdout.decode("utf-8").split("\0") if p]
    return [root / rel for rel in sorted(entries)]


def scan_file(path: pathlib.Path, rel_posix: str) -> list[str]:
    if rel_posix in ALLOWLISTED_PATHS:
        return []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [f"{rel_posix}: could not read file: {exc}"]
    if b"\x00" in raw:
        return []
    text = raw.decode("utf-8", errors="replace")
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
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
        ("macos-home", "leaked path /Users/alice/work/project\n", "/Users/alice"),
        ("linux-home", "leaked path /home/bob/work/project\n", "/home/bob"),
        (
            "windows-home",
            "leaked path C:\\Users\\carol\\work\\project\n",
            "C:\\Users\\carol",
        ),
        ("devsecops-home", "source ~/devsecops/vars/profile.sh\n", "~/devsecops"),
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
