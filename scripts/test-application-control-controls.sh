#!/usr/bin/env sh
set -eu

# Declared external invocation set:
# - POSIX sh/coreutils: repository baseline
# - goneat: JSON Schema validation named by the contract
# - python3: standard-library-only semantic validator

base="schemas/application-control/v0"
failures=0

is_semantic_negative() {
    case "$1" in
        application-descriptor/enabled-without-policy.json | \
            control-evidence/decision-from-ui.json | \
            control-message/mutation-missing-replay-guards.json | \
            control-message/payload-contract-mismatch.json | \
            control-message/unknown-operation.json | \
            control-policy/unknown-information-source.json | \
            observation-message/catalog-mode-mismatch.json | \
            operation-catalog/duplicate-operation-id.json)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

for artifact in \
    application-descriptor \
    operation-catalog \
    information-source-catalog \
    control-message \
    observation-message \
    control-evidence \
    control-policy; do
    schema="$base/$artifact.schema.json"
    fixtures="$base/fixtures/$artifact"

    for fixture in "$fixtures"/conforming/*.json; do
        [ -f "$fixture" ] || {
            printf '[!!] %s has no conforming fixtures\n' "$artifact" >&2
            failures=$((failures + 1))
            continue
        }
        if goneat validate data --schema-file "$schema" --data "$fixture" >/dev/null; then
            printf '[ok] %s\n' "$fixture"
        else
            printf '[!!] conforming fixture rejected: %s\n' "$fixture" >&2
            failures=$((failures + 1))
        fi
    done

    for fixture in "$fixtures"/negative/*.json; do
        [ -f "$fixture" ] || {
            printf '[!!] %s has no negative fixtures\n' "$artifact" >&2
            failures=$((failures + 1))
            continue
        }
        relative="$artifact/$(basename "$fixture")"
        if is_semantic_negative "$relative"; then
            if goneat validate data --schema-file "$schema" --data "$fixture" >/dev/null; then
                printf '[ok] structural pass for semantic negative: %s\n' "$fixture"
            else
                printf '[!!] semantic negative failed structural validation: %s\n' "$fixture" >&2
                failures=$((failures + 1))
            fi
        elif goneat validate data --schema-file "$schema" --data "$fixture" >/dev/null 2>&1; then
            printf '[!!] structural negative accepted: %s\n' "$fixture" >&2
            failures=$((failures + 1))
        else
            printf '[ok] structural rejection: %s\n' "$fixture"
        fi
    done
done

if [ "$failures" -ne 0 ]; then
    exit 1
fi

python3 scripts/validate-application-control-semantics.py
