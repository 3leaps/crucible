#!/usr/bin/env bash
# release-guard-release-surfaces.sh - Verify hand-maintained release surfaces match VERSION
#
# The aggregated release notes, the detailed release note, and the changelog are
# maintained by hand. Each can fall behind VERSION without any other check
# failing, so the repository can present a stale release surface from a green
# tree. This guard asserts they moved together.
#
# Checks, against the version in VERSION:
# - RELEASE_NOTES.md leads with that version's section
# - docs/releases/v<version>.md exists
# - CHANGELOG.md carries a section for that version
# - CHANGELOG.md defines that version's compare link
# - CHANGELOG.md points [unreleased] at that version
#
# Usage: ./scripts/release-guard-release-surfaces.sh

set -euo pipefail

# first_release_notes_version <release-notes-content>
# Emits the version of the first "## vX.Y.Z" heading, without the leading "v".
first_release_notes_version() {
    printf '%s\n' "$1" |
        sed -n 's/^## v\([0-9][0-9.]*\).*$/\1/p' |
        head -n 1
}

# validate_release_surfaces <version> <release-notes> <changelog> <detail-present>
# detail-present is 1 when docs/releases/v<version>.md exists, 0 otherwise.
validate_release_surfaces() {
    local version="$1"
    local release_notes="$2"
    local changelog="$3"
    local detail_present="$4"

    if [ -z "${version}" ]; then
        echo "error: VERSION is empty" >&2
        return 1
    fi

    local leading
    leading="$(first_release_notes_version "${release_notes}")"
    if [ -z "${leading}" ]; then
        echo "error: RELEASE_NOTES.md has no version section" >&2
        return 1
    fi
    if [ "${leading}" != "${version}" ]; then
        echo "error: RELEASE_NOTES.md leads with v${leading}, expected v${version}" >&2
        return 1
    fi

    if [ "${detail_present}" != "1" ]; then
        echo "error: docs/releases/v${version}.md not found" >&2
        return 1
    fi

    # Consume the whole stream. grep -q exits on the first hit (the version
    # heading is near the top) and closes the pipe; with pipefail that becomes
    # a false "missing section" once CHANGELOG is large enough for printf to
    # still be writing.
    if ! printf '%s\n' "${changelog}" | grep -F "## [${version}]" >/dev/null; then
        echo "error: CHANGELOG.md has no section for [${version}]" >&2
        return 1
    fi

    if ! printf '%s\n' "${changelog}" | grep -qE "^\[${version}\]: "; then
        echo "error: CHANGELOG.md does not define the [${version}] compare link" >&2
        return 1
    fi

    if ! printf '%s\n' "${changelog}" | grep -qE "^\[unreleased\]: .*v${version}\.\.\.HEAD$"; then
        echo "error: CHANGELOG.md [unreleased] link does not compare from v${version}" >&2
        return 1
    fi

    return 0
}

main() {
    local script_dir repo_root version release_notes changelog detail_present

    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    repo_root="$(cd "${script_dir}/.." && pwd)"

    if [ ! -f "${repo_root}/VERSION" ]; then
        echo "error: VERSION file not found" >&2
        exit 1
    fi
    version="$(tr -d '[:space:]' <"${repo_root}/VERSION")"

    if [ ! -f "${repo_root}/RELEASE_NOTES.md" ]; then
        echo "error: RELEASE_NOTES.md not found" >&2
        exit 1
    fi
    release_notes="$(cat "${repo_root}/RELEASE_NOTES.md")"

    if [ ! -f "${repo_root}/CHANGELOG.md" ]; then
        echo "error: CHANGELOG.md not found" >&2
        exit 1
    fi
    changelog="$(cat "${repo_root}/CHANGELOG.md")"

    detail_present=0
    if [ -f "${repo_root}/docs/releases/v${version}.md" ]; then
        detail_present=1
    fi

    if ! validate_release_surfaces "${version}" "${release_notes}" "${changelog}" "${detail_present}"; then
        echo "hint: see RELEASE_CHECKLIST.md (Release surfaces)" >&2
        exit 1
    fi

    echo "[ok] release surfaces match VERSION ${version}"
}

# Only run main when executed directly, so the negative controls can source this
# file and drive validate_release_surfaces with mutated content.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
