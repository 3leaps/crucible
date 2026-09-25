#!/usr/bin/env python3
"""Check, repair, or install the 3leaps attribution footer.

Every commit message and every PR body must end with exactly these three
trailer lines, after one blank line:

    Role: devlead
    Co-authored-by: <Model Name> <noreply@3leaps.net>
    Committer-of-Record: @3leapsdave

Standard-library only. No network access except the optional github-pr
subcommand, which lists PR commits through the GitHub API when running
as a GitHub Action.

Portable to macOS, Linux, and GitHub-hosted runners (Python 3.9+).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

CANONICAL_ROLE_KEY = "Role"
CANONICAL_COAUTHOR_KEY = "Co-authored-by"
CANONICAL_COR_KEY = "Committer-of-Record"

CANONICAL_COMMITTER = "@3leapsdave"

ALLOWED_DOMAINS = (
    "3leaps.net",
    "3leaps.dev",
    "fulmenhq.dev",
    "lanytehq.dev",
)

ATTRIBUTION_KEYS = {
    "role",
    "co-authored-by",
    "committer-of-record",
}

# NATO phonetic team names used as an internal prefix: <team>-<role>.
# Matching is case-insensitive. Include common spelling variants so a
# leak still fails closed rather than looking like an unknown slug.
TEAM_NAMES = (
    "alfa",
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "juliett",
    "kilo",
    "lima",
    "mike",
    "november",
    "oscar",
    "papa",
    "quebec",
    "romeo",
    "sierra",
    "tango",
    "uniform",
    "victor",
    "whiskey",
    "x-ray",
    "xray",
    "yankee",
    "zulu",
)

TEAM_PREFIX_RE = re.compile(
    r"^(?:%s)-.+" % "|".join(re.escape(name) for name in TEAM_NAMES),
    re.IGNORECASE,
)
AGENT_PREFIX_RE = re.compile(r"^agent-", re.IGNORECASE)
SLUG_RE = re.compile(r"^[a-z][a-z0-9]*$")
COAUTHOR_RE = re.compile(
    r"^(?P<name>.+?) <noreply@(?P<domain>[A-Za-z0-9.-]+)>$"
)

EXAMPLE_FOOTER = (
    f"{CANONICAL_ROLE_KEY}: devlead\n"
    f"{CANONICAL_COAUTHOR_KEY}: <Model Name> <noreply@3leaps.net>\n"
    f"{CANONICAL_COR_KEY}: {CANONICAL_COMMITTER}"
)

EXIT_OK = 0
EXIT_CHECK = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_INPUT = 4
EXIT_OUTPUT = 5


@dataclass
class Finding:
    severity: str
    message: str
    line_no: int | None = None
    got: str | None = None
    expected: str | None = None


@dataclass
class CheckResult:
    ok: bool
    findings: list[Finding] = field(default_factory=list)

    def add(
        self,
        severity: str,
        message: str,
        line_no: int | None = None,
        got: str | None = None,
        expected: str | None = None,
    ) -> None:
        self.findings.append(
            Finding(severity, message, line_no=line_no, got=got, expected=expected)
        )
        if severity == "error":
            self.ok = False


def script_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_roles_dir() -> Path:
    return script_root() / "config" / "agentic" / "roles"


def load_known_roles(roles_dir: Path | None) -> set[str]:
    directory = roles_dir if roles_dir is not None else default_roles_dir()
    if not directory.is_dir():
        return set()
    return {path.stem for path in directory.glob("*.yaml") if path.is_file()}


def strip_html_comments(text: str) -> str:
    """Drop HTML comments so PR-template / UI wrappers are not the last lines."""
    pieces: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        start = text.find("<!--", index)
        if start == -1:
            pieces.append(text[index:])
            break
        pieces.append(text[index:start])
        end = text.find("-->", start + 4)
        if end == -1:
            break
        index = end + 3
    return "".join(pieces)


def normalize_text(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_html_comments(text)
    return text


def split_trailer(line: str) -> tuple[str | None, str]:
    stripped = line.strip()
    if ":" not in stripped:
        return None, stripped
    key, value = stripped.split(":", 1)
    if not key or any(ch.isspace() for ch in key):
        return None, stripped
    return key, value.strip()


def canonical_key(key: str) -> str | None:
    lowered = key.lower()
    if lowered == "role":
        return CANONICAL_ROLE_KEY
    if lowered == "co-authored-by":
        return CANONICAL_COAUTHOR_KEY
    if lowered == "committer-of-record":
        return CANONICAL_COR_KEY
    return None


def example_footer_block() -> str:
    return (
        "Required footer (last three non-empty lines, after one blank line):\n\n"
        f"{EXAMPLE_FOOTER}\n"
    )


def format_finding(finding: Finding) -> str:
    location = f"line {finding.line_no}: " if finding.line_no is not None else ""
    lines = [f"{finding.severity}: {location}{finding.message}"]
    if finding.got is not None:
        lines.append(f"  got:      {finding.got}")
    if finding.expected is not None:
        lines.append(f"  expected: {finding.expected}")
    return "\n".join(lines)


def emit_github_annotation(finding: Finding) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    if finding.severity not in {"error", "warning", "notice"}:
        return
    message = finding.message.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
    extra = ""
    if finding.line_no is not None:
        extra = f",line={finding.line_no}"
    sys.stderr.write(f"::{finding.severity}{extra}::{message}\n")


def print_result(result: CheckResult, *, source: str | None = None) -> None:
    if source:
        sys.stderr.write(f"checking {source}\n")
    for finding in result.findings:
        emit_github_annotation(finding)
        sys.stderr.write(format_finding(finding) + "\n")
    if not result.ok:
        sys.stderr.write("\n" + example_footer_block())


def render_footer(role: str, model: str, domain: str, committer: str) -> str:
    return (
        f"{CANONICAL_ROLE_KEY}: {role}\n"
        f"{CANONICAL_COAUTHOR_KEY}: {model} <noreply@{domain}>\n"
        f"{CANONICAL_COR_KEY}: {committer}"
    )


def split_body_and_trailing_trailers(text: str) -> tuple[str, list[str]]:
    normalized = normalize_text(text)
    lines = normalized.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    footer_start = len(lines)
    while footer_start > 0:
        key, _ = split_trailer(lines[footer_start - 1])
        if key is not None and key.lower() in ATTRIBUTION_KEYS:
            footer_start -= 1
            continue
        break
    body_lines = lines[:footer_start]
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    return "\n".join(body_lines), lines[footer_start:]


def validate_role(value: str, known_roles: set[str], line_no: int, result: CheckResult) -> None:
    if AGENT_PREFIX_RE.match(value):
        result.add(
            "error",
            "Role must be a bare role slug; never agent-*",
            line_no=line_no,
            got=f"{CANONICAL_ROLE_KEY}: {value}",
            expected=f"{CANONICAL_ROLE_KEY}: devlead",
        )
        return
    if TEAM_PREFIX_RE.match(value):
        result.add(
            "error",
            "Role must be a bare role slug; team-prefixed names "
            "(for example bravo-devlead) leak on public repos",
            line_no=line_no,
            got=f"{CANONICAL_ROLE_KEY}: {value}",
            expected=f"{CANONICAL_ROLE_KEY}: devlead",
        )
        return
    if not SLUG_RE.match(value):
        result.add(
            "error",
            "Role must be a bare lowercase slug "
            "(leading letter, then lowercase letters or digits)",
            line_no=line_no,
            got=f"{CANONICAL_ROLE_KEY}: {value}",
            expected=f"{CANONICAL_ROLE_KEY}: devlead",
        )
        return
    if known_roles and value not in known_roles:
        result.add(
            "warning",
            f"Role {value!r} is not in crucible's role catalog "
            f"({default_roles_dir()}); seats may use their own slug",
            line_no=line_no,
            got=f"{CANONICAL_ROLE_KEY}: {value}",
        )


def validate_coauthor(value: str, line_no: int, result: CheckResult) -> None:
    match = COAUTHOR_RE.fullmatch(value)
    domains = ", ".join(ALLOWED_DOMAINS)
    expected = f"{CANONICAL_COAUTHOR_KEY}: <Model Name> <noreply@3leaps.net>"
    if match is None:
        result.add(
            "error",
            "Co-authored-by must be '<Model Name> <noreply@DOMAIN>' with "
            f"DOMAIN one of {domains}",
            line_no=line_no,
            got=f"{CANONICAL_COAUTHOR_KEY}: {value}",
            expected=expected,
        )
        return
    name = match.group("name").strip()
    domain = match.group("domain")
    if not name:
        result.add(
            "error",
            "Co-authored-by model name must be non-empty",
            line_no=line_no,
            got=f"{CANONICAL_COAUTHOR_KEY}: {value}",
            expected=expected,
        )
        return
    if domain not in ALLOWED_DOMAINS:
        result.add(
            "error",
            f"Co-authored-by domain {domain!r} is not allowed; "
            f"use one of {domains}",
            line_no=line_no,
            got=f"{CANONICAL_COAUTHOR_KEY}: {value}",
            expected=expected,
        )


def validate_committer(value: str, line_no: int, result: CheckResult) -> None:
    if value != CANONICAL_COMMITTER:
        result.add(
            "error",
            f"Committer-of-Record must be exactly {CANONICAL_COMMITTER}",
            line_no=line_no,
            got=f"{CANONICAL_COR_KEY}: {value}",
            expected=f"{CANONICAL_COR_KEY}: {CANONICAL_COMMITTER}",
        )


def drop_extra_coauthors(
    non_empty: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    trimmed = list(non_empty)
    while len(trimmed) > 3:
        key, _ = split_trailer(trimmed[-1][1])
        if key is not None and key.lower() == "co-authored-by":
            trimmed.pop()
            continue
        break
    return trimmed


def check_text(
    text: str,
    *,
    mode: str = "pr-body",
    known_roles: set[str] | None = None,
) -> CheckResult:
    result = CheckResult(ok=True)
    roles = known_roles if known_roles is not None else load_known_roles(None)
    normalized = normalize_text(text)
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()

    numbered_nonempty = [
        (index + 1, line) for index, line in enumerate(lines) if line != ""
    ]
    if mode == "commit":
        numbered_nonempty = drop_extra_coauthors(numbered_nonempty)

    if len(numbered_nonempty) < 3:
        result.add(
            "error",
            "attribution footer is missing or incomplete "
            "(need Role, Co-authored-by, and Committer-of-Record)",
        )
        return result

    last_three = numbered_nonempty[-3:]
    expected_keys = (
        CANONICAL_ROLE_KEY,
        CANONICAL_COAUTHOR_KEY,
        CANONICAL_COR_KEY,
    )
    parsed: list[tuple[int, str, str | None, str, str]] = []
    for line_no, line in last_three:
        key, value = split_trailer(line)
        canon = canonical_key(key) if key is not None else None
        parsed.append((line_no, line, canon, key or "", value))

    got_keys = tuple(item[2] for item in parsed)
    if got_keys != expected_keys:
        got_desc = ", ".join(item[2] or item[1] for item in parsed)
        result.add(
            "error",
            "last three non-empty lines must be Role, Co-authored-by, "
            "Committer-of-Record in that order",
            line_no=parsed[0][0],
            got=got_desc,
            expected=", ".join(expected_keys),
        )
        return result

    role_line_no = parsed[0][0]
    if role_line_no <= 1 or lines[role_line_no - 2] != "":
        result.add(
            "error",
            "attribution footer must be preceded by a blank line",
            line_no=role_line_no,
            got=parsed[0][1],
        )

    for line_no, line, canon, raw_key, value in parsed:
        if canon is not None and raw_key != canon:
            result.add(
                "notice",
                f"trailer key {raw_key!r} is accepted (git trailer keys are "
                f"case-insensitive); canonical spelling is {canon!r}",
                line_no=line_no,
                got=line,
                expected=f"{canon}: {value}",
            )
        if canon == CANONICAL_ROLE_KEY:
            validate_role(value, roles, line_no, result)
        elif canon == CANONICAL_COAUTHOR_KEY:
            validate_coauthor(value, line_no, result)
        elif canon == CANONICAL_COR_KEY:
            validate_committer(value, line_no, result)

    return result


def read_source(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    file_path = Path(path)
    try:
        return file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}") from exc


def write_source(path: str, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    if path == "-":
        sys.stdout.write(text)
        return
    file_path = Path(path)
    try:
        file_path.write_text(text, encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"error: cannot write {path}: {exc}\n")
        raise SystemExit(EXIT_OUTPUT) from exc


def parse_domain(domain: str) -> str:
    if domain not in ALLOWED_DOMAINS:
        allowed = ", ".join(ALLOWED_DOMAINS)
        sys.stderr.write(
            f"error: domain {domain!r} is not allowed; use one of {allowed}\n"
        )
        raise SystemExit(EXIT_USAGE)
    return domain


def parse_role_arg(role: str) -> str:
    if not role or not SLUG_RE.match(role) or AGENT_PREFIX_RE.match(role) or TEAM_PREFIX_RE.match(role):
        sys.stderr.write(
            "error: --role must be a bare lowercase slug "
            "(not agent-* and not team-prefixed)\n"
        )
        raise SystemExit(EXIT_USAGE)
    return role


def parse_model_arg(model: str) -> str:
    cleaned = model.strip()
    if not cleaned or "<" in cleaned or ">" in cleaned:
        sys.stderr.write(
            "error: --model must be a non-empty model name without <angle brackets>\n"
        )
        raise SystemExit(EXIT_USAGE)
    return cleaned


def append_footer(
    text: str,
    *,
    role: str,
    model: str,
    domain: str,
    committer: str,
) -> str:
    body, _trailing = split_body_and_trailing_trailers(text)
    footer = render_footer(role, model, domain, committer)
    if body:
        return f"{body}\n\n{footer}\n"
    return f"\n{footer}\n"


def resolve_roles_dir(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    return None


def cmd_check(args: argparse.Namespace) -> int:
    source = args.path
    try:
        text = read_source(source)
    except SystemExit as exc:
        message = str(exc)
        if message:
            sys.stderr.write(message + "\n")
        return EXIT_INPUT
    known = load_known_roles(resolve_roles_dir(args.roles_dir))
    label = "stdin" if source == "-" else source
    result = check_text(text, mode=args.mode, known_roles=known)
    print_result(result, source=label)
    if result.ok:
        sys.stderr.write("ok: attribution footer\n")
        return EXIT_OK
    return EXIT_CHECK


def cmd_append(args: argparse.Namespace) -> int:
    role = parse_role_arg(args.role)
    model = parse_model_arg(args.model)
    domain = parse_domain(args.domain)
    committer = args.committer
    if committer != CANONICAL_COMMITTER:
        sys.stderr.write(
            f"error: --committer must be exactly {CANONICAL_COMMITTER}\n"
        )
        return EXIT_USAGE
    source = args.path
    try:
        text = read_source(source)
    except SystemExit as exc:
        message = str(exc)
        if message:
            sys.stderr.write(message + "\n")
        return EXIT_INPUT
    updated = append_footer(
        text, role=role, model=model, domain=domain, committer=committer
    )
    write_source(source, updated)
    known = load_known_roles(resolve_roles_dir(args.roles_dir))
    result = check_text(updated, mode="pr-body", known_roles=known)
    print_result(result, source="stdin" if source == "-" else source)
    if not result.ok:
        return EXIT_CHECK
    sys.stderr.write("ok: attribution footer appended\n")
    return EXIT_OK


def env_or_none(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def cmd_commit_msg(args: argparse.Namespace) -> int:
    path = args.path
    role = args.role or env_or_none("ATTRIBUTION_ROLE")
    model = args.model or env_or_none("ATTRIBUTION_MODEL")
    domain = args.domain or env_or_none("ATTRIBUTION_DOMAIN")
    committer = args.committer or env_or_none("ATTRIBUTION_COMMITTER") or CANONICAL_COMMITTER
    try:
        text = read_source(path)
    except SystemExit as exc:
        message = str(exc)
        if message:
            sys.stderr.write(message + "\n")
        return EXIT_INPUT

    if role and model and domain:
        parse_role_arg(role)
        parse_model_arg(model)
        parse_domain(domain)
        if committer != CANONICAL_COMMITTER:
            sys.stderr.write(
                f"error: committer must be exactly {CANONICAL_COMMITTER}\n"
            )
            return EXIT_USAGE
        text = append_footer(
            text, role=role, model=model, domain=domain, committer=committer
        )
        write_source(path, text)
    elif any(value is not None for value in (role, model, domain)):
        sys.stderr.write(
            "error: commit-msg append needs --role/--model/--domain "
            "or ATTRIBUTION_ROLE, ATTRIBUTION_MODEL, and ATTRIBUTION_DOMAIN\n"
        )
        return EXIT_USAGE

    known = load_known_roles(resolve_roles_dir(args.roles_dir))
    result = check_text(text, mode="commit", known_roles=known)
    print_result(result, source=path)
    if not result.ok:
        if not (role and model and domain):
            sys.stderr.write(
                "hint: set ATTRIBUTION_ROLE, ATTRIBUTION_MODEL, and "
                "ATTRIBUTION_DOMAIN to append the footer from this hook\n"
            )
        return EXIT_CHECK
    sys.stderr.write("ok: attribution footer\n")
    return EXIT_OK


def git_dir() -> Path | None:
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        git = candidate / ".git"
        if git.is_dir():
            return git
        if git.is_file():
            try:
                data = git.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            if data.startswith("gitdir:"):
                return (candidate / data.split(":", 1)[1].strip()).resolve()
    return None


def hook_script_body() -> str:
    return """#!/usr/bin/env bash
# 3leaps attribution footer — git commit-msg hook
set -euo pipefail

toplevel="$(git rev-parse --show-toplevel)"
candidates=(
    "${ATTRIBUTION_CHECKER:-}"
    "${CRUCIBLE_ROOT:-}/scripts/check-attribution.py"
    "${toplevel}/scripts/check-attribution.py"
    "${toplevel}/../crucible/scripts/check-attribution.py"
)

checker=""
for candidate in "${candidates[@]}"; do
    if [ -n "${candidate}" ] && [ -f "${candidate}" ]; then
        checker="${candidate}"
        break
    fi
done

if [ -z "${checker}" ]; then
    echo "error: cannot find check-attribution.py" >&2
    echo "Set ATTRIBUTION_CHECKER or CRUCIBLE_ROOT, or clone 3leaps/crucible as a sibling." >&2
    exit 1
fi

exec python3 "${checker}" commit-msg "$1"
"""


def cmd_install_hook(args: argparse.Namespace) -> int:
    git = git_dir()
    if git is None:
        sys.stderr.write("error: not a git repository\n")
        return EXIT_CONFIG
    hook = git / "hooks" / "commit-msg"
    hook.parent.mkdir(parents=True, exist_ok=True)
    if hook.exists() and not args.force:
        existing = hook.read_text(encoding="utf-8")
        if "check-attribution.py" not in existing:
            sys.stderr.write(
                f"error: {hook} already exists; pass --force to replace it\n"
            )
            return EXIT_OUTPUT
    hook.write_text(hook_script_body(), encoding="utf-8")
    hook.chmod(hook.stat().st_mode | 0o111)
    sys.stderr.write(f"ok: installed commit-msg hook at {hook}\n")
    return EXIT_OK


def api_request(url: str, token: str) -> tuple[dict | list, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "3leaps-crucible-attribution-footer",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
            headers = {key.lower(): value for key, value in response.headers.items()}
            return payload, headers
    except urllib.error.HTTPError as exc:
        sys.stderr.write(f"error: GitHub API request failed: {exc.code} {exc.reason}\n")
        raise SystemExit(EXIT_CHECK) from exc
    except urllib.error.URLError as exc:
        sys.stderr.write(f"error: GitHub API request failed: {exc.reason}\n")
        raise SystemExit(EXIT_CHECK) from exc


def next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        start = section.find("<")
        end = section.find(">")
        if start != -1 and end != -1:
            return section[start + 1 : end]
    return None


def fetch_commit_messages(
    api_url: str, repo: str, number: int, token: str
) -> list[tuple[str, str]]:
    url = f"{api_url.rstrip('/')}/repos/{repo}/pulls/{number}/commits?per_page=100"
    commits: list[tuple[str, str]] = []
    while url:
        payload, headers = api_request(url, token)
        if not isinstance(payload, list):
            sys.stderr.write("error: unexpected GitHub commits response\n")
            raise SystemExit(EXIT_CHECK)
        for item in payload:
            sha = str(item.get("sha") or "")[:12]
            message = (
                ((item.get("commit") or {}).get("message"))
                if isinstance(item, dict)
                else None
            )
            commits.append((sha, message if isinstance(message, str) else ""))
        url = next_link(headers.get("link"))
    return commits


def cmd_github_pr(args: argparse.Namespace) -> int:
    event_path = args.event_file or os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        sys.stderr.write("error: GITHUB_EVENT_PATH is not set\n")
        return EXIT_CONFIG
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: cannot read GitHub event file: {exc}\n")
        return EXIT_INPUT

    pull = event.get("pull_request")
    if not isinstance(pull, dict):
        sys.stderr.write("error: github-pr requires a pull_request event payload\n")
        return EXIT_CONFIG
    body = pull.get("body")
    if body is None:
        body = ""
    if not isinstance(body, str):
        sys.stderr.write("error: pull_request.body is not a string\n")
        return EXIT_INPUT

    known = load_known_roles(resolve_roles_dir(args.roles_dir))
    result = check_text(body, mode="pr-body", known_roles=known)
    print_result(result, source="pull_request.body")
    failed = not result.ok

    check_commits = args.check_commits
    if check_commits is None:
        check_commits = os.environ.get("CHECK_COMMITS", "").lower() in {
            "1",
            "true",
            "yes",
        }
    if check_commits:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        repo = os.environ.get("GITHUB_REPOSITORY") or ""
        api_url = os.environ.get("GITHUB_API_URL") or "https://api.github.com"
        number = pull.get("number")
        if not token:
            sys.stderr.write(
                "error: GITHUB_TOKEN is required when checking PR commits\n"
            )
            return EXIT_CONFIG
        if not repo or not isinstance(number, int):
            sys.stderr.write(
                "error: GITHUB_REPOSITORY and pull_request.number are required "
                "when checking PR commits\n"
            )
            return EXIT_CONFIG
        commits = fetch_commit_messages(api_url, repo, number, token)
        if not commits:
            sys.stderr.write("error: pull request has no commits to check\n")
            failed = True
        for sha, message in commits:
            commit_result = check_text(message, mode="commit", known_roles=known)
            print_result(commit_result, source=f"commit {sha}")
            if not commit_result.ok:
                failed = True

    if failed:
        return EXIT_CHECK
    sys.stderr.write("ok: attribution footer\n")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check-attribution.py",
        description="Check or append the 3leaps attribution footer.",
    )
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser("check", help="validate a commit message or PR body")
    check.add_argument("path", help="file to check, or - for stdin")
    check.add_argument(
        "--mode",
        choices=("pr-body", "commit"),
        default="pr-body",
        help="pr-body (default) requires the footer at the end; "
        "commit allows extra trailing Co-authored-by lines",
    )
    check.add_argument("--roles-dir", default=None, help="role catalog directory")
    check.set_defaults(func=cmd_check)

    append = sub.add_parser(
        "append", help="append or replace a trailing attribution footer"
    )
    append.add_argument("path", help="file to update, or - for stdin/stdout")
    append.add_argument("--role", required=True, help="bare role slug")
    append.add_argument("--model", required=True, help="model display name")
    append.add_argument(
        "--domain",
        required=True,
        help="noreply domain (3leaps.net, 3leaps.dev, fulmenhq.dev, lanytehq.dev)",
    )
    append.add_argument(
        "--committer",
        default=CANONICAL_COMMITTER,
        help=f"Committer-of-Record (must be {CANONICAL_COMMITTER})",
    )
    append.add_argument("--roles-dir", default=None, help="role catalog directory")
    append.set_defaults(func=cmd_append)

    commit_msg = sub.add_parser(
        "commit-msg", help="git commit-msg hook entry (append if env/flags set)"
    )
    commit_msg.add_argument("path", help="path to COMMIT_EDITMSG")
    commit_msg.add_argument("--role", default=None)
    commit_msg.add_argument("--model", default=None)
    commit_msg.add_argument("--domain", default=None)
    commit_msg.add_argument("--committer", default=None)
    commit_msg.add_argument("--roles-dir", default=None)
    commit_msg.set_defaults(func=cmd_commit_msg)

    install = sub.add_parser(
        "install-hook", help="install a commit-msg hook in the current git repo"
    )
    install.add_argument(
        "--force", action="store_true", help="replace an existing commit-msg hook"
    )
    install.set_defaults(func=cmd_install_hook)

    github_pr = sub.add_parser(
        "github-pr", help="validate a GitHub pull_request event (used by the Action)"
    )
    github_pr.add_argument(
        "--event-file",
        default=None,
        help="path to the GitHub event JSON (defaults to GITHUB_EVENT_PATH)",
    )
    github_pr.add_argument(
        "--check-commits",
        action="store_true",
        default=None,
        help="also check each PR commit message (commit mode)",
    )
    github_pr.add_argument("--roles-dir", default=None)
    github_pr.set_defaults(func=cmd_github_pr)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    argv_list = list(sys.argv if argv is None else argv)
    if argv is None:
        prog = argv_list[0] if argv_list else ""
        args = argv_list[1:]
    else:
        prog = argv_list[0] if argv_list else "check-attribution.py"
        args = argv_list[1:]

    if os.path.basename(prog) == "commit-msg":
        parser = build_parser()
        parsed = parser.parse_args(["commit-msg", *args])
        return int(parsed.func(parsed))

    parser = build_parser()
    parsed = parser.parse_args(args)
    if not getattr(parsed, "command", None):
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    return int(parsed.func(parsed))


if __name__ == "__main__":
    raise SystemExit(main())
