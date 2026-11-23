#!/usr/bin/env bash
# Negative controls for release-guard-release-surfaces.sh.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The source path is resolved relative to this script at runtime.
# shellcheck disable=SC1091
source "${script_dir}/release-guard-release-surfaces.sh"

version='0.1.23'

valid_release_notes='# Release Notes

---

## v0.1.23 (2026-07-26)

**A governance release.**

---

## v0.1.22 (2026-07-22)

**An earlier release.**
'

valid_changelog='# Changelog

## [Unreleased]

## [0.1.23] - 2026-07-26

### Added

- A record.

## [0.1.22] - 2026-07-22

### Added

- An earlier record.

[unreleased]: https://github.com/3leaps/crucible/compare/v0.1.23...HEAD
[0.1.23]: https://github.com/3leaps/crucible/compare/v0.1.22...v0.1.23
[0.1.22]: https://github.com/3leaps/crucible/compare/v0.1.21...v0.1.22
'

expect_accepted() {
    local description="$1"
    shift
    if ! validate_release_surfaces "$@" >/dev/null 2>&1; then
        echo "error: positive control was rejected: ${description}" >&2
        exit 1
    fi
    echo "[ok] accepted: ${description}"
}

# expect_rejected <description> <expected-message-fragment> <guard args...>
# The fragment pins which assertion fired. Without it a mutation broken in some
# other dimension would report as a pass.
expect_rejected() {
    local description="$1"
    local expected="$2"
    shift 2
    local output
    if output="$(validate_release_surfaces "$@" 2>&1)"; then
        echo "error: negative control was accepted: ${description}" >&2
        exit 1
    fi
    if [[ "${output}" != *"${expected}"* ]]; then
        echo "error: rejected for the wrong reason: ${description}" >&2
        echo "  expected message to contain: ${expected}" >&2
        echo "  actual: ${output}" >&2
        exit 1
    fi
    echo "[ok] rejected: ${description}"
}

# Case zero: the unmutated fixture must pass, or every rejection below is
# uninformative — a fixture broken in some other dimension would also "fail".
expect_accepted "exact release surfaces" \
    "${version}" "${valid_release_notes}" "${valid_changelog}" 1

# mutate <content> <sed-expression>
# Each mutation edits exactly one dimension of an otherwise valid fixture.
mutate() {
    printf '%s\n' "$1" | sed "$2"
}

# RELEASE_NOTES.md — the miss this guard was added for.
expect_rejected "release notes lead with the previous version" \
    "RELEASE_NOTES.md leads with v0.1.21" \
    "${version}" "$(mutate "${valid_release_notes}" 's/^## v0\.1\.23 .*/## v0.1.21 (2026-07-20)/')" "${valid_changelog}" 1

expect_rejected "release notes carry no version section" \
    "RELEASE_NOTES.md has no version section" \
    "${version}" "# Release Notes

No sections yet.
" "${valid_changelog}" 1

# The detailed per-release note.
expect_rejected "detailed release note absent" \
    "docs/releases/v0.1.23.md not found" \
    "${version}" "${valid_release_notes}" "${valid_changelog}" 0

# CHANGELOG.md — section and both footer links.
expect_rejected "changelog has no section for the version" \
    "no section for [0.1.23]" \
    "${version}" "${valid_release_notes}" "$(mutate "${valid_changelog}" 's/^## \[0\.1\.23\]/## [0.1.23-rc.1]/')" 1

expect_rejected "changelog does not define the version compare link" \
    "does not define the [0.1.23] compare link" \
    "${version}" "${valid_release_notes}" "$(mutate "${valid_changelog}" '/^\[0\.1\.23\]: /d')" 1

expect_rejected "changelog unreleased link still compares from the previous version" \
    "[unreleased] link does not compare from v0.1.23" \
    "${version}" "${valid_release_notes}" "$(mutate "${valid_changelog}" 's|v0\.1\.23\.\.\.HEAD|v0.1.22...HEAD|')" 1

# A large changelog whose matching lines come first. A guard that pipes into
# grep -q under pipefail fails here deterministically: grep exits on the early
# match and the still-writing producer dies of SIGPIPE.
large_changelog="$(
    printf '%s\n' "${valid_changelog}" | sed -n '/^\[unreleased\]/,$p'
    printf '%s\n' "${valid_changelog}" | sed '/^\[/d'
    for _ in $(seq 1 20000); do printf '%s\n' '- Filler entry to keep the producer writing.'; done
)"
expect_accepted "early matches in a large changelog" \
    "${version}" "${valid_release_notes}" "${large_changelog}" 1

# Version carriers: package.json and the README badge.
valid_readme='# Project

![Version: 0.1.23](https://img.shields.io/badge/version-0.1.23-blue)
'

if ! validate_version_carriers "${version}" 1 "0.1.23" "${valid_readme}" >/dev/null 2>&1; then
    echo "error: positive control was rejected: version carriers" >&2
    exit 1
fi
echo "[ok] accepted: version carriers"

if ! validate_version_carriers "${version}" 0 "" "${valid_readme}" >/dev/null 2>&1; then
    echo "error: positive control was rejected: no package.json" >&2
    exit 1
fi
echo "[ok] accepted: repository without package.json"

commented_readme='# Project

<!-- ![Version: 0.1.22](https://img.shields.io/badge/version-0.1.22-blue) -->
![Version: 0.1.23](https://img.shields.io/badge/version-0.1.23-blue)
'
if ! validate_version_carriers "${version}" 1 "0.1.23" "${commented_readme}" >/dev/null 2>&1; then
    echo "error: positive control was rejected: commented stale badge" >&2
    exit 1
fi
echo "[ok] accepted: a commented-out badge is ignored"

expect_carrier_rejected() {
    local description="$1"
    local expected="$2"
    shift 2
    local output
    if output="$(validate_version_carriers "$@" 2>&1)"; then
        echo "error: negative control was accepted: ${description}" >&2
        exit 1
    fi
    if [[ "${output}" != *"${expected}"* ]]; then
        echo "error: rejected for the wrong reason: ${description}" >&2
        echo "  actual: ${output}" >&2
        exit 1
    fi
    echo "[ok] rejected: ${description}"
}

expect_carrier_rejected "package.json carries the previous version" \
    "package.json version is 0.1.22, expected 0.1.23" \
    "${version}" 1 "0.1.22" "${valid_readme}"

expect_carrier_rejected "package.json version is empty" \
    "package.json version is , expected 0.1.23" \
    "${version}" 1 "" "${valid_readme}"

expect_carrier_rejected "package.json version is the literal dash" \
    "package.json version is -, expected 0.1.23" \
    "${version}" 1 "-" "${valid_readme}"

expect_carrier_rejected "README badge names the previous version" \
    "exactly one version badge naming 0.1.23" \
    "${version}" 1 "0.1.23" "$(mutate "${valid_readme}" 's/0\.1\.23/0.1.22/g')"

expect_carrier_rejected "README has no badge" \
    "exactly one version badge naming 0.1.23" \
    "${version}" 1 "0.1.23" "# Project"

expect_carrier_rejected "only badge is commented out" \
    "exactly one version badge naming 0.1.23" \
    "${version}" 1 "0.1.23" "# Project

<!-- ![Version: 0.1.23](https://img.shields.io/badge/version-0.1.23-blue) -->"

expect_carrier_rejected "stale visible badge beside a correct commented one" \
    "exactly one version badge naming 0.1.23" \
    "${version}" 1 "0.1.23" "# Project

![Version: 0.1.22](https://img.shields.io/badge/version-0.1.22-blue)
<!-- ![Version: 0.1.23](https://img.shields.io/badge/version-0.1.23-blue) -->"

expect_carrier_rejected "two visible badges, one stale" \
    "exactly one version badge naming 0.1.23" \
    "${version}" 1 "0.1.23" "${valid_readme}
![Version: 0.1.22](https://img.shields.io/badge/version-0.1.22-blue)"

fence='```'
expect_carrier_rejected "only badge sits inside a fenced example" \
    "exactly one version badge naming 0.1.23" \
    "${version}" 1 "0.1.23" "# Project

${fence}markdown
![Version: 0.1.23](https://img.shields.io/badge/version-0.1.23-blue)
${fence}"

fenced_example_readme="${valid_readme}

Example:

${fence}markdown
![Version: 0.1.22](https://img.shields.io/badge/version-0.1.22-blue)
${fence}
"
if ! validate_version_carriers "${version}" 1 "0.1.23" "${fenced_example_readme}" >/dev/null 2>&1; then
    echo "error: positive control was rejected: header badge plus a fenced example" >&2
    exit 1
fi
echo "[ok] accepted: header badge with a fenced example below it"

expect_carrier_rejected "badge appears only after prose" \
    "exactly one version badge naming 0.1.23" \
    "${version}" 1 "0.1.23" "# Project

Some prose first.

![Version: 0.1.23](https://img.shields.io/badge/version-0.1.23-blue)"

expect_carrier_rejected "badge colour changed" \
    "exactly one version badge naming 0.1.23" \
    "${version}" 1 "0.1.23" "$(mutate "${valid_readme}" 's/-blue/-red/')"

# Guard inputs themselves.
expect_rejected "empty version" \
    "VERSION is empty" \
    "" "${valid_release_notes}" "${valid_changelog}" 1

echo "[ok] release-surface guard negative controls passed"
