#!/usr/bin/env bash
#
# sync-changelog-links.sh - Sync CHANGELOG compare-link footers to VERSION
#
# Usage: ./scripts/sync-changelog-links.sh
#
# Updates the Keep a Changelog footer links after VERSION is bumped:
# - [unreleased] compares v<VERSION>...HEAD
# - [VERSION] compares v<previous>...v<VERSION>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION_FILE="${REPO_ROOT}/VERSION"
CHANGELOG_FILE="${REPO_ROOT}/CHANGELOG.md"

if [[ ! -f "$VERSION_FILE" ]]; then
    echo "[!!] VERSION file not found: $VERSION_FILE"
    exit 1
fi

if [[ ! -f "$CHANGELOG_FILE" ]]; then
    echo "[!!] CHANGELOG.md not found: $CHANGELOG_FILE"
    exit 1
fi

VERSION=$(tr -d '[:space:]' <"$VERSION_FILE")

version_gt() {
    local left_major left_minor left_patch
    local right_major right_minor right_patch

    IFS=. read -r left_major left_minor left_patch <<<"$1"
    IFS=. read -r right_major right_minor right_patch <<<"$2"

    if ((left_major != right_major)); then
        ((left_major > right_major))
        return
    fi
    if ((left_minor != right_minor)); then
        ((left_minor > right_minor))
        return
    fi
    ((left_patch > right_patch))
}

if [[ -z "$VERSION" ]]; then
    echo "[!!] VERSION file is empty"
    exit 1
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "[!!] Invalid version format: $VERSION (expected x.y.z)"
    exit 1
fi

UNRELEASED_LINE=$(grep -E '^\[unreleased\]:' "$CHANGELOG_FILE" | head -1 || true)

if [[ -z "$UNRELEASED_LINE" ]]; then
    echo "[!!] Could not find [unreleased] compare-link footer in CHANGELOG.md"
    exit 1
fi

if [[ ! "$UNRELEASED_LINE" =~ ^\[unreleased\]:[[:space:]]*(.*)v([0-9]+\.[0-9]+\.[0-9]+)\.\.\.HEAD$ ]]; then
    echo "[!!] Could not parse [unreleased] compare-link footer:"
    echo "    $UNRELEASED_LINE"
    echo "    Expected: [unreleased]: <compare-url>/vX.Y.Z...HEAD"
    exit 1
fi

COMPARE_PREFIX="${BASH_REMATCH[1]}"
PREVIOUS_VERSION="${BASH_REMATCH[2]}"
NEW_UNRELEASED="[unreleased]: ${COMPARE_PREFIX}v${VERSION}...HEAD"
NEW_VERSION_DEF="[${VERSION}]: ${COMPARE_PREFIX}v${PREVIOUS_VERSION}...v${VERSION}"

HAS_VERSION_DEF=0
if grep -qE "^\[${VERSION//./\\.}\]:" "$CHANGELOG_FILE"; then
    HAS_VERSION_DEF=1
fi

if [[ "$PREVIOUS_VERSION" == "$VERSION" && "$HAS_VERSION_DEF" -eq 1 ]]; then
    echo "[ok] CHANGELOG compare links already synced for $VERSION"
    exit 0
fi

if [[ "$PREVIOUS_VERSION" == "$VERSION" ]]; then
    echo "[!!] [unreleased] already starts at $VERSION, but [$VERSION] is missing"
    echo "    Cannot infer the previous release for the [$VERSION] compare link."
    exit 1
fi

if ! version_gt "$VERSION" "$PREVIOUS_VERSION"; then
    echo "[!!] Refusing to sync CHANGELOG compare links backwards: $PREVIOUS_VERSION -> $VERSION"
    exit 1
fi

TMP_FILE=$(mktemp)

awk \
    -v version="$VERSION" \
    -v new_unreleased="$NEW_UNRELEASED" \
    -v new_version_def="$NEW_VERSION_DEF" \
    -v has_version_def="$HAS_VERSION_DEF" \
    '
    BEGIN {
        version_label = "[" version "]:"
    }

    /^\[unreleased\]:/ {
        print new_unreleased
        if (has_version_def == 0) {
            print new_version_def
        }
        next
    }

    index($0, version_label) == 1 {
        print new_version_def
        next
    }

    {
        print
    }
    ' "$CHANGELOG_FILE" >"$TMP_FILE"

mv "$TMP_FILE" "$CHANGELOG_FILE"

if [[ "$HAS_VERSION_DEF" -eq 1 ]]; then
    echo "[ok] CHANGELOG compare links updated for $VERSION"
else
    echo "[ok] CHANGELOG compare links added: $PREVIOUS_VERSION -> $VERSION"
fi
