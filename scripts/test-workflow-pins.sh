#!/usr/bin/env bash
# Validate GitHub Actions workflow supply-chain pins and permission boundaries:
#   1. Every non-local `uses:` pin uses a 40-hex commit SHA and `# v...` comment.
#   2. Every `container:` image pin carries an immutable `@sha256:<64-hex>` digest.
#   3. Workflow and job `permissions:` blocks stay within least-privilege bounds
#      (`contents: write` restricted to the `create-release` job in `release.yml`).
# Includes EPR-0002 negative controls proving unpinned actions, digestless
# containers, and broadened permissions fail closed.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflows_dir="${repo_root}/.github/workflows"

check_workflows_dir() {
    local target_dir="$1"
    python3 - "${target_dir}" <<'PY'
import pathlib
import re
import sys

USES_RE = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}\s+#\s*v[0-9A-Za-z._-]+(?:\s.*)?$"
)
IMAGE_DIGEST_RE = re.compile(r"^[^\s#]+@sha256:[0-9a-f]{64}$")
ALLOWED_READ_SCOPES = {"contents", "pull-requests", "actions"}


def strip_comment(raw: str) -> str:
    in_single = False
    in_double = False
    for idx, ch in enumerate(raw):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if idx == 0 or raw[idx - 1].isspace():
                return raw[:idx].strip()
    return raw.strip()


def unquote(val: str) -> str:
    if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
        return val[1:-1]
    return val


def check_workflow(path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    is_release = path.name == "release.yml"

    block_scalar_indent: int | None = None
    in_jobs = False
    jobs_indent = 0
    current_job: str | None = None
    job_indent: int | None = None

    in_permissions = False
    permissions_indent = 0
    permissions_job: str | None = None
    permissions_entries = 0
    saw_top_permissions = False

    in_container = False
    container_indent = 0
    container_saw_image = False
    container_line = 0

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))

        if block_scalar_indent is not None:
            if indent > block_scalar_indent:
                continue
            block_scalar_indent = None

        if in_permissions and indent <= permissions_indent:
            if permissions_entries == 0:
                errors.append(f"{path.name}:{lineno}: empty permissions mapping")
            in_permissions = False
            permissions_job = None

        if in_container and indent <= container_indent:
            if not container_saw_image:
                errors.append(
                    f"{path.name}:{container_line}: container block missing digest-pinned image"
                )
            in_container = False

        if in_jobs and indent <= jobs_indent:
            in_jobs = False
            current_job = None
            job_indent = None

        if in_jobs:
            if job_indent is None and indent > jobs_indent and not stripped.startswith("-"):
                m_job = re.match(r"^([A-Za-z0-9_-]+):\s*(?:#.*)?$", stripped)
                if m_job:
                    current_job = m_job.group(1)
                    job_indent = indent
            elif job_indent is not None and indent == job_indent and not stripped.startswith("-"):
                m_job = re.match(r"^([A-Za-z0-9_-]+):\s*(?:#.*)?$", stripped)
                if m_job:
                    current_job = m_job.group(1)

        m_kv = re.match(r"^(?:-\s+)?([A-Za-z0-9_-]+):\s*(.*)$", stripped)
        if not m_kv:
            continue

        key, raw_val = m_kv.group(1), m_kv.group(2)
        clean_val = strip_comment(raw_val)

        if clean_val in ("|", ">", "|-", ">-", "|+", ">+"):
            block_scalar_indent = indent
            continue

        if indent == 0 and key == "jobs" and clean_val == "":
            in_jobs = True
            jobs_indent = indent
            current_job = None
            job_indent = None
            continue

        if in_permissions and indent > permissions_indent:
            permissions_entries += 1
            scope = key
            level = unquote(clean_val)
            if level == "write":
                if is_release and permissions_job == "create-release" and scope == "contents":
                    pass
                else:
                    ctx = f"job '{permissions_job}'" if permissions_job else "workflow top-level"
                    errors.append(
                        f"{path.name}:{lineno}: forbidden write permission '{scope}: {level}' in {ctx}"
                    )
            elif level in ("read", "none"):
                if scope not in ALLOWED_READ_SCOPES:
                    errors.append(
                        f"{path.name}:{lineno}: unexpected permission scope '{scope}: {level}'"
                    )
            else:
                errors.append(
                    f"{path.name}:{lineno}: invalid permission level '{scope}: {level}'"
                )
            continue

        if key == "permissions":
            if indent == 0:
                saw_top_permissions = True
                permissions_job = None
            else:
                permissions_job = current_job
            if clean_val != "":
                errors.append(
                    f"{path.name}:{lineno}: permissions must be an explicit mapping, got '{clean_val}'"
                )
            else:
                in_permissions = True
                permissions_indent = indent
                permissions_entries = 0
            continue

        if in_container and indent > container_indent:
            if key == "image":
                container_saw_image = True
                img = unquote(clean_val)
                if not IMAGE_DIGEST_RE.match(img):
                    errors.append(
                        f"{path.name}:{lineno}: container image '{img}' must be pinned by @sha256:<64-hex>"
                    )
            continue

        if key == "container":
            if clean_val != "":
                img = unquote(clean_val)
                if not IMAGE_DIGEST_RE.match(img):
                    errors.append(
                        f"{path.name}:{lineno}: container image '{img}' must be pinned by @sha256:<64-hex>"
                    )
            else:
                in_container = True
                container_indent = indent
                container_saw_image = False
                container_line = lineno
            continue

        if key == "uses":
            if raw_val.startswith("./") or clean_val.startswith("./"):
                continue
            if not USES_RE.match(raw_val):
                errors.append(
                    f"{path.name}:{lineno}: action '{raw_val}' must be pinned to a 40-hex commit SHA with '# v...' comment"
                )

    if in_permissions and permissions_entries == 0:
        errors.append(f"{path.name}: empty permissions mapping")
    if in_container and not container_saw_image:
        errors.append(
            f"{path.name}:{container_line}: container block missing digest-pinned image"
        )
    if not saw_top_permissions:
        errors.append(f"{path.name}: missing top-level permissions block")

    return errors


target = pathlib.Path(sys.argv[1])
files = sorted(target.glob("*.yml"))
if not files:
    sys.stderr.write(f"error: no workflow .yml files found in {target}\n")
    sys.exit(1)

all_errors: list[str] = []
for wf in files:
    all_errors.extend(check_workflow(wf))

if all_errors:
    for err in all_errors:
        sys.stderr.write(f"error: {err}\n")
    sys.exit(1)
PY
}

# 1. Verify committed repository workflows.
check_workflows_dir "${workflows_dir}"

# 2. EPR-0002 negative controls: synthetic violations must fail closed.
tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

expect_reject() {
    local label="$1"
    local file="$2"
    local pattern="$3"
    local err_out
    if err_out="$(check_workflows_dir "${file}" 2>&1)"; then
        echo "error: negative control '${label}' unexpectedly passed" >&2
        exit 1
    fi
    if ! grep -Fq "${pattern}" <<<"${err_out}"; then
        echo "error: negative control '${label}' failed without expected message '${pattern}':" >&2
        echo "${err_out}" >&2
        exit 1
    fi
}

mkdir -p "${tmp_dir}/tag-pin"
cat >"${tmp_dir}/tag-pin/ci.yml" <<'EOF'
name: CI
on: [push]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
EOF
expect_reject "tag-pinned action" "${tmp_dir}/tag-pin" "must be pinned to a 40-hex commit SHA"

mkdir -p "${tmp_dir}/no-comment"
cat >"${tmp_dir}/no-comment/ci.yml" <<'EOF'
name: CI
on: [push]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd
EOF
expect_reject "SHA pin without version comment" "${tmp_dir}/no-comment" "must be pinned to a 40-hex commit SHA with '# v...' comment"

mkdir -p "${tmp_dir}/digestless-container"
cat >"${tmp_dir}/digestless-container/ci.yml" <<'EOF'
name: CI
on: [push]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: alpine:3.21
    steps:
      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd  # v5.0.1
EOF
expect_reject "digestless container image" "${tmp_dir}/digestless-container" "must be pinned by @sha256:<64-hex>"

mkdir -p "${tmp_dir}/broad-perms"
cat >"${tmp_dir}/broad-perms/ci.yml" <<'EOF'
name: CI
on: [push]
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd  # v5.0.1
EOF
expect_reject "broadened workflow permissions" "${tmp_dir}/broad-perms" "forbidden write permission 'contents: write'"

echo "[ok] workflow SHA pins, container digests, and permission boundaries verified"
