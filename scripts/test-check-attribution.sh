#!/usr/bin/env bash
# Controls for scripts/check-attribution.py.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
checker="${script_dir}/check-attribution.py"
roles_dir="${script_dir}/../config/agentic/roles"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

footer() {
    local role="${1:-devlead}"
    local model="${2:-Grok 4.6}"
    local domain="${3:-3leaps.dev}"
    printf '%s\n' \
        "Role: ${role}" \
        "Co-authored-by: ${model} <noreply@${domain}>" \
        "Committer-of-Record: @3leapsdave"
}

valid_message() {
    printf '%s\n' "feat(demo): add example" "" "Body of the change." ""
    footer "$@"
}

expect_exit() {
    local want="$1"
    local description="$2"
    shift 2
    local status=0
    "$@" >"${tmp}/stdout" 2>"${tmp}/stderr" || status=$?
    if [ "${status}" -ne "${want}" ]; then
        echo "error: ${description}: expected exit ${want}, got ${status}" >&2
        echo "stdout:" >&2
        cat "${tmp}/stdout" >&2
        echo "stderr:" >&2
        cat "${tmp}/stderr" >&2
        exit 1
    fi
    echo "[ok] ${description}"
}

expect_stderr_grep() {
    local pattern="$1"
    local description="$2"
    if ! grep -Eq "${pattern}" "${tmp}/stderr"; then
        echo "error: ${description}: stderr did not match ${pattern}" >&2
        cat "${tmp}/stderr" >&2
        exit 1
    fi
    echo "[ok] ${description}"
}

python3 "${checker}" >/dev/null 2>&1 && {
    echo "error: running with no args should fail" >&2
    exit 1
}
echo "[ok] usage without a command exits nonzero"

valid_message >"${tmp}/valid.txt"
expect_exit 0 "valid footer" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/valid.txt"

printf '%s\n' "feat(demo): add example" "" "Body of the change." >"${tmp}/missing.txt"
expect_exit 1 "missing footer" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/missing.txt"
expect_stderr_grep "attribution footer is missing" "missing footer names the problem"

{
    printf '%s\n' "feat(demo): add example" ""
    printf '%s\n' \
        "Co-authored-by: Grok 4.6 <noreply@3leaps.dev>" \
        "Role: devlead" \
        "Committer-of-Record: @3leapsdave"
} >"${tmp}/wrong-order.txt"
expect_exit 1 "wrong trailer order" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/wrong-order.txt"
expect_stderr_grep "Role, Co-authored-by, Committer-of-Record" "wrong-order error names the expected order"

{
    printf '%s\n' "feat(demo): add example" ""
    footer "bravo-devlead"
} >"${tmp}/team-prefix.txt"
expect_exit 1 "team-prefixed role bravo-devlead" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/team-prefix.txt"
expect_stderr_grep "team-prefixed" "bravo-devlead error mentions team-prefixed names"

{
    printf '%s\n' "feat(demo): add example" ""
    footer "agent-devlead"
} >"${tmp}/agent-prefix.txt"
expect_exit 1 "agent-devlead role" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/agent-prefix.txt"
expect_stderr_grep "never agent-\*" "agent-devlead error mentions agent-*"

{
    printf '%s\n' "feat(demo): add example" ""
    footer "devlead" "Grok 4.6" "example.com"
} >"${tmp}/bad-domain.txt"
expect_exit 1 "disallowed Co-authored-by domain" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/bad-domain.txt"
expect_stderr_grep "domain 'example.com' is not allowed" "bad domain names the value"

{
    printf '%s\n' "feat(demo): add example" ""
    printf '%s\n' \
        "Role: devlead" \
        "Co-authored-by: Grok 4.6 <noreply@3leaps.dev>" \
        "Committer-of-Record: @someoneelse"
} >"${tmp}/wrong-committer.txt"
expect_exit 1 "wrong Committer-of-Record" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/wrong-committer.txt"
expect_stderr_grep "exactly @3leapsdave" "wrong committer names the required handle"

valid_message | sed 's/$/\r/' >"${tmp}/crlf.txt"
expect_exit 0 "CRLF line endings" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/crlf.txt"

{
    printf '%s\n' "feat(demo): add example" "" "Body of the change." ""
    printf '%s\n' "Role: devlead"
} >"${tmp}/partial.txt"
expect_exit 1 "partial footer before append" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/partial.txt"
expect_exit 0 "append repairs a partial footer" \
    python3 "${checker}" append --roles-dir "${roles_dir}" \
    --role devlead --model "Grok 4.6" --domain 3leaps.dev "${tmp}/partial.txt"
expect_exit 0 "repaired partial footer checks clean" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/partial.txt"
if ! grep -q "Committer-of-Record: @3leapsdave" "${tmp}/partial.txt"; then
    echo "error: append did not write Committer-of-Record" >&2
    exit 1
fi
echo "[ok] append repaired a partial footer"

cp "${tmp}/partial.txt" "${tmp}/once.txt"
expect_exit 0 "append is idempotent" \
    python3 "${checker}" append --roles-dir "${roles_dir}" \
    --role devlead --model "Grok 4.6" --domain 3leaps.dev "${tmp}/partial.txt"
if ! cmp -s "${tmp}/once.txt" "${tmp}/partial.txt"; then
    echo "error: second append changed a complete footer" >&2
    diff -u "${tmp}/once.txt" "${tmp}/partial.txt" >&2 || true
    exit 1
fi
echo "[ok] append idempotency"

{
    printf '%s\n' "feat(demo): add example" ""
    footer "wright"
} >"${tmp}/unknown-role.txt"
expect_exit 0 "unknown catalog role warns rather than fails" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/unknown-role.txt"
expect_stderr_grep "warning:.*Role 'wright' is not in" "unknown role prints a warning"

{
    printf '%s\n' "feat(demo): add example" ""
    printf '%s\n' \
        "Role: devlead" \
        "Co-Authored-By: Grok 4.6 <noreply@3leaps.dev>" \
        "Committer-of-Record: @3leapsdave"
} >"${tmp}/key-case.txt"
expect_exit 0 "Co-Authored-By casing is accepted" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/key-case.txt"
expect_stderr_grep "notice:.*Co-Authored-By" "non-canonical Co-authored-by key emits a notice"

{
    printf '%s\n' "feat(demo): add example" ""
    footer
    printf '%s\n' "Co-authored-by: Reviewer <reviewer@example.com>"
} >"${tmp}/extra-coauthor.txt"
expect_exit 1 "PR body mode rejects extra trailing Co-authored-by" \
    python3 "${checker}" check --mode pr-body --roles-dir "${roles_dir}" \
    "${tmp}/extra-coauthor.txt"
expect_exit 0 "commit mode allows extra trailing Co-authored-by" \
    python3 "${checker}" check --mode commit --roles-dir "${roles_dir}" \
    "${tmp}/extra-coauthor.txt"

{
    printf '%s\n' "feat(demo): add example" ""
    footer
    printf '%s\n' "" "<!-- CURSOR_AGENT_PR_BODY_END -->"
} >"${tmp}/html-comment.txt"
expect_exit 0 "trailing HTML comments are ignored" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/html-comment.txt"

{
    printf '%s\n' "feat(demo): add example" ""
    footer
    printf '%s\n' "" \
        "<!-- CURSOR_AGENT_PR_BODY_END -->" \
        "<div><a href=\"https://example.com\"><img alt=\"Open in Web\"></a></div>"
} >"${tmp}/html-badge.txt"
expect_exit 0 "trailing HTML badge markup is ignored" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/html-badge.txt"

valid_message | expect_exit 0 "stdin check" \
    python3 "${checker}" check --roles-dir "${roles_dir}" -

expect_exit 0 "commit-msg appends from flags" \
    python3 "${checker}" commit-msg --roles-dir "${roles_dir}" \
    --role devlead --model "Grok 4.6" --domain 3leaps.dev "${tmp}/missing.txt"
expect_exit 0 "commit-msg result checks clean" \
    python3 "${checker}" check --mode commit --roles-dir "${roles_dir}" \
    "${tmp}/missing.txt"

cat >"${tmp}/event.json" <<EOF
{
  "pull_request": {
    "number": 1,
    "body": "feat(demo): add example\n\nBody of the change.\n\nRole: devlead\nCo-authored-by: Grok 4.6 <noreply@3leaps.dev>\nCommitter-of-Record: @3leapsdave\n"
  }
}
EOF
expect_exit 0 "github-pr reads the event file" \
    python3 "${checker}" github-pr --event-file "${tmp}/event.json" \
    --roles-dir "${roles_dir}"

footer >"${tmp}/footer-only.txt"
expect_exit 0 "footer-only snippet does not need a leading blank line" \
    python3 "${checker}" check --roles-dir "${roles_dir}" "${tmp}/footer-only.txt"

examples_dir="${tmp}/examples"
mkdir -p "${examples_dir}"

cat >"${examples_dir}/good.md" <<'EOF'
# Good examples

A complete commit-message example:

```
feat(demo): add example

Body of the change.

Role: devlead
Co-authored-by: Grok 4.6 <noreply@3leaps.dev>
Committer-of-Record: @3leapsdave
```

A footer-only snippet:

```
Role: devlead
Co-authored-by: Grok 4.6 <noreply@3leaps.dev>
Committer-of-Record: @3leapsdave
```
EOF

cat >"${examples_dir}/bad.md" <<'EOF'
# Bad example

```
feat(demo): add example

Co-authored-by: Grok 4.6 <noreply@3leaps.dev>
Role: devlead
Committer-of-Record: @3leapsdave
```
EOF

cat >"${examples_dir}/skipped.md" <<'EOF'
# Counter-examples that must not fail the scan

<!-- attribution: invalid-example -->
```
Role: bravo-devlead
Co-authored-by: Grok 4.6 <noreply@3leaps.dev>
Committer-of-Record: @3leapsdave
```

```attribution-invalid
Role: agent-devlead
Co-authored-by: Grok 4.6 <noreply@3leaps.dev>
Committer-of-Record: @3leapsdave
```
EOF

cat >"${examples_dir}/roles.yaml" <<'EOF'
examples:
  - type: commit
    title: Feature implementation
    content: |
      feat(demo): add example

      Body of the change.

      Role: devlead
      Co-authored-by: Grok 4.6 <noreply@3leaps.dev>
      Committer-of-Record: @3leapsdave

  - type: commit
    title: Leaky team prefix
    # attribution: invalid-example
    content: |
      feat(demo): add example

      Role: bravo-devlead
      Co-authored-by: Grok 4.6 <noreply@3leaps.dev>
      Committer-of-Record: @3leapsdave
EOF

expect_exit 0 "markdown mode accepts good fenced examples" \
    python3 "${checker}" check --markdown --roles-dir "${roles_dir}" \
    "${examples_dir}/good.md"
expect_exit 0 "markdown mode expands a quoted glob" \
    python3 "${checker}" check --markdown --roles-dir "${roles_dir}" \
    "${examples_dir}/good.*"
expect_exit 1 "markdown mode fails a bad fenced example" \
    python3 "${checker}" check --markdown --roles-dir "${roles_dir}" \
    "${examples_dir}/bad.md"
expect_stderr_grep "bad.md:[0-9]+:" "markdown failure reports file:line"
expect_stderr_grep "Role, Co-authored-by, Committer-of-Record" \
    "markdown failure names the wrong-order reason"
expect_exit 0 "markdown mode skips marked counter-examples" \
    python3 "${checker}" check --markdown --roles-dir "${roles_dir}" \
    "${examples_dir}/skipped.md"
expect_stderr_grep "skip:.*attribution: invalid-example" \
    "HTML skip comment is reported"
expect_stderr_grep "skip:.*attribution-invalid" \
    "info-string skip is reported"
expect_exit 0 "markdown mode extracts YAML block-scalar examples" \
    python3 "${checker}" check --markdown --roles-dir "${roles_dir}" \
    "${examples_dir}/roles.yaml"
expect_stderr_grep "skip:.*attribution: invalid-example" \
    "YAML hash skip is reported"
expect_exit 1 "markdown mode scans a directory and fails on a bad block" \
    python3 "${checker}" check --markdown --roles-dir "${roles_dir}" \
    "${examples_dir}"
expect_exit 0 "attribution-footer.md examples follow the new rule" \
    python3 "${checker}" check --markdown --roles-dir "${roles_dir}" \
    "${script_dir}/../docs/repository/attribution-footer.md"

echo "[ok] attribution footer controls passed"
