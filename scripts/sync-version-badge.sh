#!/usr/bin/env bash
#
# sync-version-badge.sh - Sync version from VERSION file to README badge
#
# Usage: ./scripts/sync-version-badge.sh
#
# Updates the version badge in README.md to match the VERSION file.
# Uses sed for cross-platform compatibility.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VERSION_FILE="${REPO_ROOT}/VERSION"
README_FILE="${REPO_ROOT}/README.md"

# Check files exist
if [[ ! -f "$VERSION_FILE" ]]; then
    echo "[!!] VERSION file not found: $VERSION_FILE"
    exit 1
fi

if [[ ! -f "$README_FILE" ]]; then
    echo "[!!] README.md not found: $README_FILE"
    exit 1
fi

# Read current version
VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')

if [[ -z "$VERSION" ]]; then
    echo "[!!] VERSION file is empty"
    exit 1
fi

# Validate version format (semver-like: x.y.z)
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "[!!] Invalid version format: $VERSION (expected x.y.z)"
    exit 1
fi

# Extract current badge version using grep
CURRENT_BADGE=$(grep -oE 'version-[0-9]+\.[0-9]+\.[0-9]+' "$README_FILE" | head -1 | sed 's/version-//' || true)

if [[ -z "$CURRENT_BADGE" ]]; then
    echo "[!!] Could not find version badge in README.md"
    echo "    Expected format: ![Version: x.y.z](https://img.shields.io/badge/version-x.y.z-blue)"
    exit 1
fi

if [[ "$CURRENT_BADGE" == "$VERSION" ]]; then
    echo "[ok] README badge already at version $VERSION"
    exit 0
fi

# Update badge using sed (macOS and Linux compatible)
# Match both the label text and the URL part of the badge
# Badge format: ![Version: x.y.z](https://img.shields.io/badge/version-x.y.z-blue)

# Create temp file for atomic update
TMP_FILE=$(mktemp)

# Perform the replacements
sed -E \
    -e "s/Version: [0-9]+\.[0-9]+\.[0-9]+/Version: ${VERSION}/g" \
    -e "s/version-[0-9]+\.[0-9]+\.[0-9]+/version-${VERSION}/g" \
    "$README_FILE" >"$TMP_FILE"

# Move temp file to original
mv "$TMP_FILE" "$README_FILE"

echo "[ok] README badge updated: $CURRENT_BADGE -> $VERSION"
