#!/usr/bin/env sh
# Conformance battery for contract: agent-wait/v0.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils, find — baseline
#   goneat — subject-matter (JSON Schema validation the contract names)
#   jq — structural inspection of contract fixtures (house pattern)
#   python3 — subject-matter runtime for portable RFC3339 instants
#
# Asserts:
#   - every declared message kind has a golden example that validates
#   - schema-labeled baseline-* pass and reject-* fail schema validation
#   - normative-labeled fixtures are schema-valid; baselines pass and
#     reject-* fail the normative checker with the expected reason
#   - set fixtures are schema-valid and fail only at the set/normative gate
#   - schema and single-file normative pairs differ in exactly one field
#   - the cross-contract job_complete path is well-formed
#   - fixtures contain no credentials, raw tokens, or machine-local paths
#   - RFC3339 profile accepted; non-RFC3339 ISO and leap seconds fail closed
#   - a missing, unreadable, empty, malformed, or space-named target fails
#   - a single file and a directory of valid records still pass
set -eu

base="schemas/agent-wait/v0"
schema="$base/agent-wait-message.schema.json"

ndiff_jq='
def ndiff(a; b):
  if (a | type) != (b | type) then 1
  elif (a | type) == "object" then
    ((((a | keys) + (b | keys)) | unique)
     | map(. as $k |
         if ((a | has($k)) and (b | has($k))) then ndiff(a[$k]; b[$k])
         else 1 end)
     | add) // 0
  elif (a | type) == "array" then
    (if (a | length) != (b | length) then 1 else 0 end)
    + (([range(0; ([(a | length), (b | length)] | min))]
        | map(. as $i | ndiff(a[$i]; b[$i]))
        | add) // 0)
  elif a == b then 0
  else 1
  end;
'

pair_distance() {
    jq -n --slurpfile a "$1" --slurpfile b "$2" "$ndiff_jq ndiff(\$a; \$b)"
}

assert_pair_distance_one() {
    pd=$(pair_distance "$1" "$2")
    if [ "$pd" -ne 1 ]; then
        echo "    [!!] reject/baseline pair differs in $pd fields, not exactly 1: $2" >&2
        exit 1
    fi
}

hygiene_scan() {
    root=$1
    if grep -R -E -n \
        '(:\/\/[^[:space:]"]*@)|(^|[\"[:space:]])file:\/\/|\/home\/|\/Users\/|\/tmp\/|\/var\/|[A-Za-z]:\\\\|Bearer[[:space:]]|sk-[A-Za-z0-9]|api[_-]?key=|access_token=' \
        --include='*.json' "$root" >/dev/null 2>&1; then
        echo "    [!!] fixture hygiene failed under $root" >&2
        grep -R -E -n \
            '(:\/\/[^[:space:]"]*@)|(^|[\"[:space:]])file:\/\/|\/home\/|\/Users\/|\/tmp\/|\/var\/|[A-Za-z]:\\\\|Bearer[[:space:]]|sk-[A-Za-z0-9]|api[_-]?key=|access_token=' \
            --include='*.json' "$root" >&2 || true
        exit 1
    fi
}

expected_reason() {
    name=$1
    case "$name" in
        *deadline-ordering*) echo deadline_ordering ;;
        *no-change-with-events* | *no-change-past-deadline*) echo no_change_invariants ;;
        *deadman-before-deadline*) echo deadman_invariants ;;
        *outage-as-no-change* | *uncertain-as-deadman* | *degraded-as-no-change* | *degraded-as-deadman*) echo outage_not_clean ;;
        *coverage-cardinality*) echo coverage_cardinality ;;
        *ack-past-unretained*) echo ack_past_unretained ;;
        *silent-cursor-advance*) echo silent_cursor_advance ;;
        *revision-cross*) echo revision_cross ;;
        *fairness-starvation*) echo fairness_starvation ;;
        *authn-required*) echo authn_required ;;
        *lease-expired*) echo lease_reauth ;;
        *registration-bound*) echo registration_bound ;;
        *aggregate-bound*) echo aggregate_bound ;;
        *cross-arm-commit*) echo cross_arm_commit ;;
        *) echo unknown ;;
    esac
}

assert_normative_target_gate() {
    script=$1
    golden=$2
    baseline_dir=$3
    work=$(mktemp -d)

    if sh "$script" /definitely/missing/path >/tmp/aw-tgt.out 2>/tmp/aw-tgt.err; then
        echo "    [!!] missing path was accepted by $script" >&2
        exit 1
    fi
    if sh "$script" "/definitely/missing/path with spaces" >/tmp/aw-tgt.out 2>/tmp/aw-tgt.err; then
        echo "    [!!] missing path with spaces was accepted by $script" >&2
        exit 1
    fi

    cp "$golden" "$work/unreadable.json"
    chmod 000 "$work/unreadable.json"
    if sh "$script" "$work/unreadable.json" >/tmp/aw-tgt.out 2>/tmp/aw-tgt.err; then
        echo "    [!!] unreadable file was accepted by $script" >&2
        chmod 600 "$work/unreadable.json"
        exit 1
    fi
    chmod 600 "$work/unreadable.json"

    mkdir -p "$work/unreadable-dir"
    cp "$golden" "$work/unreadable-dir/ok.json"
    chmod 000 "$work/unreadable-dir"
    if sh "$script" "$work/unreadable-dir" >/tmp/aw-tgt.out 2>/tmp/aw-tgt.err; then
        echo "    [!!] unreadable directory was accepted by $script" >&2
        chmod 700 "$work/unreadable-dir"
        exit 1
    fi
    chmod 700 "$work/unreadable-dir"

    mkdir -p "$work/empty-dir"
    if sh "$script" "$work/empty-dir" >/tmp/aw-tgt.out 2>/tmp/aw-tgt.err; then
        echo "    [!!] empty directory was accepted by $script" >&2
        exit 1
    fi

    printf '%s\n' '{not-json' >"$work/malformed.json"
    if sh "$script" "$work/malformed.json" >/tmp/aw-tgt.out 2>/tmp/aw-tgt.err; then
        echo "    [!!] malformed JSON was accepted by $script" >&2
        exit 1
    fi

    mkdir -p "$work/space-dir"
    printf '%s\n' '{not-json' >"$work/space-dir/broken name.json"
    if sh "$script" "$work/space-dir" >/tmp/aw-tgt.out 2>/tmp/aw-tgt.err; then
        echo "    [!!] space-named malformed JSON was accepted by $script" >&2
        exit 1
    fi

    sh "$script" "$golden" || {
        echo "    [!!] single-file golden failed $script: $golden" >&2
        exit 1
    }
    sh "$script" "$baseline_dir" || {
        echo "    [!!] directory baseline failed $script: $baseline_dir" >&2
        exit 1
    }

    mkdir -p "$work/space-ok"
    cp "$golden" "$work/space-ok/wait outcome.json"
    sh "$script" "$work/space-ok" || {
        echo "    [!!] valid space-named file failed $script" >&2
        exit 1
    }
    rm -rf "$work"
}

echo "    RFC3339 instant self-test..."
python3 scripts/rfc3339-instant.py --self-test || {
    echo "    [!!] RFC3339 instant self-test failed" >&2
    exit 1
}
if python3 scripts/rfc3339-instant.py --epoch "not-a-timestamp" >/tmp/aw-ts.out 2>/tmp/aw-ts.err; then
    echo "    [!!] unparseable timestamp was accepted" >&2
    exit 1
fi
# Direct probes: ISO 8601 forms that datetime.fromisoformat accepts must
# still fail closed. Leap second 60 is rejected, not clamped.
for bad in \
    "20260815T170000Z" \
    "2026-W33-6T17:00:00Z" \
    "2026-227T17:00:00Z" \
    "2026-08-15T17:00Z" \
    "2026-08-15T17:00:00+0000" \
    "2026-08-15 17:00:00Z" \
    "2016-12-31T23:59:60Z"; do
    if python3 scripts/rfc3339-instant.py --epoch "$bad" >/tmp/aw-ts.out 2>/tmp/aw-ts.err; then
        echo "    [!!] non-RFC3339 instant was accepted: $bad" >&2
        exit 1
    fi
done
python3 scripts/rfc3339-instant.py --epoch "2026-08-15T17:00:00Z" >/tmp/aw-ts.out
python3 scripts/rfc3339-instant.py --epoch "2026-08-15T17:00:00.123Z" >/tmp/aw-ts.frac
python3 scripts/rfc3339-instant.py --epoch "2026-08-15T17:00:00+00:00" >/tmp/aw-ts.off
if [ "$(cat /tmp/aw-ts.out)" != "$(cat /tmp/aw-ts.off)" ]; then
    echo "    [!!] Z and +00:00 must be the same instant" >&2
    exit 1
fi
if [ "$(cat /tmp/aw-ts.out)" != "$(cat /tmp/aw-ts.frac)" ]; then
    echo "    [!!] fractional seconds must not change integer epoch" >&2
    exit 1
fi
if [ "$(python3 scripts/rfc3339-instant.py --compare "2026-08-15T17:00:00+00:00" "2026-08-15T17:00:00Z")" != "0" ]; then
    echo "    [!!] offset-equivalent instants must compare equal" >&2
    exit 1
fi
echo "    [ok] RFC3339 profile accepted; non-RFC3339 ISO and leap seconds fail closed"

echo "    Normative target resolution..."
assert_normative_target_gate \
    scripts/validate-agent-wait-normative.sh \
    "$base/examples/registration_set.example.json" \
    "$base/rejects/set/baseline-authn-optional"
echo "    [ok] missing, unreadable, empty, malformed, and space-named targets fail closed"

echo "    Frozen outcome kinds (live and poll)..."
for kind in events no_change logical_deadman partial cancelled coverage_degraded refused reauthentication_required failed; do
    for mode in live_wait_outcome poll_cycle_outcome; do
        f="$base/examples/outcomes/${mode}.${kind}.json"
        [ -f "$f" ] || {
            echo "    [!!] missing $mode $kind: $f" >&2
            exit 1
        }
        goneat validate data --schema-file "$schema" --data "$f" >/dev/null
        sh scripts/validate-agent-wait-normative.sh "$f"
        echo "    [ok] outcome $mode $kind"
    done
done

echo "    Positive coverage (one golden per declared kind)..."
for kind in registration_set live_wait_request live_wait_outcome poll_cycle_request poll_cycle_outcome poll_cycle_ack; do
    f="$base/examples/${kind}.example.json"
    [ -f "$f" ] || {
        echo "    [!!] missing golden for $kind: $f" >&2
        exit 1
    }
    goneat validate data --schema-file "$schema" --data "$f" >/dev/null
    sh scripts/validate-agent-wait-normative.sh "$f"
    echo "    [ok] golden: $f"
done

echo "    Registration priority goldens..."
for priority in 0 50 100 255; do
    f="$base/examples/registration_set.priority-$priority.example.json"
    [ -f "$f" ] || {
        echo "    [!!] missing priority golden: $f" >&2
        exit 1
    }
    goneat validate data --schema-file "$schema" --data "$f" >/dev/null
    sh scripts/validate-agent-wait-normative.sh "$f"
    echo "    [ok] priority golden: $f"
done

omitted="$base/examples/registration_set.example.json"
explicit_50="$base/examples/registration_set.priority-50.example.json"
jq -n -e --slurpfile omitted "$omitted" --slurpfile explicit "$explicit_50" '
    ($omitted[0].registrations)
    == ($explicit[0].registrations | map(del(.priority)))
    and ($explicit[0].registrations | all(.priority == 50))
' >/dev/null || {
    echo "    [!!] omitted and explicit-50 registrations are not exact priority twins" >&2
    exit 1
}
omitted_digest=$(jq -c '.registrations' "$omitted" | python3 scripts/rfc8785-canonicalize.py | sha256sum | awk '{print $1}')
explicit_50_digest=$(jq -c '.registrations' "$explicit_50" | python3 scripts/rfc8785-canonicalize.py | sha256sum | awk '{print $1}')
if [ "$omitted_digest" != "$(jq -r '.registration_digest.value' "$omitted")" ] ||
    [ "$explicit_50_digest" != "$(jq -r '.registration_digest.value' "$explicit_50")" ] ||
    [ "$omitted_digest" = "$explicit_50_digest" ]; then
    echo "    [!!] omitted and explicit-50 priority digest invariant failed" >&2
    exit 1
fi
echo "    [ok] omitted and explicit-50 registrations share content but differ in JCS digest"

echo "    Schema-labeled controls..."
for f in "$base"/rejects/schema/baseline-*.json; do
    [ -f "$f" ] || continue
    goneat validate data --schema-file "$schema" --data "$f" >/dev/null || {
        echo "    [!!] schema baseline failed validation: $f" >&2
        exit 1
    }
    echo "    [ok] schema baseline passes: $f"
done
for f in "$base"/rejects/schema/reject-*.json; do
    [ -f "$f" ] || continue
    if goneat validate data --schema-file "$schema" --data "$f" >/dev/null 2>&1; then
        echo "    [!!] schema reject passed validation: $f" >&2
        exit 1
    fi
    echo "    [ok] schema rejected: $f"
done

echo "    Normative-labeled controls..."
for f in "$base"/rejects/normative/baseline-*.json; do
    [ -f "$f" ] || continue
    goneat validate data --schema-file "$schema" --data "$f" >/dev/null || {
        echo "    [!!] normative baseline is not schema-valid: $f" >&2
        exit 1
    }
    sh scripts/validate-agent-wait-normative.sh "$f" || {
        echo "    [!!] normative baseline failed normative check: $f" >&2
        exit 1
    }
    echo "    [ok] normative baseline passes: $f"
done
for f in "$base"/rejects/normative/reject-*.json; do
    [ -f "$f" ] || continue
    goneat validate data --schema-file "$schema" --data "$f" >/dev/null || {
        echo "    [!!] normative reject is not schema-valid: $f" >&2
        exit 1
    }
    if sh scripts/validate-agent-wait-normative.sh "$f" >/tmp/aw-norm.out 2>/tmp/aw-norm.err; then
        echo "    [!!] normative reject passed the normative check: $f" >&2
        exit 1
    fi
    got=$(sed -n 's/^normative_reason: //p' /tmp/aw-norm.err | head -n 1)
    want=$(expected_reason "${f##*/}")
    if [ "$got" != "$want" ]; then
        echo "    [!!] expected reason $want, got ${got:-<none>}: $f" >&2
        cat /tmp/aw-norm.err >&2
        exit 1
    fi
    echo "    [ok] normative rejected ($got): $f"
done

echo "    Set fixtures..."
for d in "$base"/rejects/set/baseline-* "$base"/rejects/set/reject-*; do
    [ -d "$d" ] || continue
    for f in "$d"/*.json; do
        [ -f "$f" ] || continue
        goneat validate data --schema-file "$schema" --data "$f" >/dev/null || {
            echo "    [!!] set fixture is not schema-valid: $f" >&2
            exit 1
        }
    done
done
for d in "$base"/rejects/set/baseline-*; do
    [ -d "$d" ] || continue
    sh scripts/validate-agent-wait-normative.sh "$d" || {
        echo "    [!!] baseline set failed: $d" >&2
        exit 1
    }
    echo "    [ok] baseline set passes: $d"
done
for d in "$base"/rejects/set/reject-*; do
    [ -d "$d" ] || continue
    if sh scripts/validate-agent-wait-normative.sh "$d" >/tmp/aw-norm.out 2>/tmp/aw-norm.err; then
        echo "    [!!] set reject passed the normative check: $d" >&2
        exit 1
    fi
    got=$(sed -n 's/^normative_reason: //p' /tmp/aw-norm.err | head -n 1)
    want=$(expected_reason "${d##*/}")
    if [ "$got" != "$want" ]; then
        echo "    [!!] expected reason $want, got ${got:-<none>}: $d" >&2
        cat /tmp/aw-norm.err >&2
        exit 1
    fi
    echo "    [ok] rejected set ($got): $d"
done

echo "    Pair-distance invariant (schema and single-file normative pairs)..."
for f in "$base"/rejects/schema/reject-*.json "$base"/rejects/normative/reject-*.json; do
    [ -f "$f" ] || continue
    twin="$(dirname "$f")/baseline-${f##*/reject-}"
    # Some normative rejects share a thematic baseline with a different stem.
    if [ ! -f "$twin" ]; then
        case "${f##*/}" in
            reject-no-change-with-events.json) twin="$(dirname "$f")/baseline-no-change-empty.json" ;;
            reject-no-change-past-deadline.json) twin="$(dirname "$f")/baseline-no-change-before-deadline.json" ;;
            reject-deadman-before-deadline.json) twin="$(dirname "$f")/baseline-deadman-at-deadline.json" ;;
            reject-outage-as-no-change.json | reject-degraded-as-no-change.json) twin="$(dirname "$f")/baseline-no-change-arm.json" ;;
            reject-uncertain-as-deadman.json | reject-degraded-as-deadman.json) twin="$(dirname "$f")/baseline-deadman-arm.json" ;;
            reject-event-id-anchor.json) twin="$(dirname "$f")/baseline-opaque-anchor.json" ;;
            *)
                echo "    [!!] reject has no baseline twin: $f" >&2
                exit 1
                ;;
        esac
    fi
    assert_pair_distance_one "$twin" "$f"
    echo "    [ok] pair distance 1: $f"
done

echo "    Cross-contract job_complete path..."
goneat validate data --schema-file "$schema" --data "$base/examples/cross-path/registration_set.job_complete.json" >/dev/null
goneat validate data --schema-file "$schema" --data "$base/examples/cross-path/poll_cycle_outcome.job_complete.json" >/dev/null
sh scripts/validate-agent-wait-normative.sh "$base/examples/cross-path/registration_set.job_complete.json"
sh scripts/validate-agent-wait-normative.sh "$base/examples/cross-path/poll_cycle_outcome.job_complete.json"
# observe_hint is supplied by service-job; this registration must add a start position.
jq -e '.registrations[] | (has("start_anchor") or has("baseline_policy")) and ((has("start_anchor") and has("baseline_policy")) | not)' \
    "$base/examples/cross-path/registration_set.job_complete.json" >/dev/null
jq -e '.events[0].method_id == "job_complete" and .events[0].subject_kind == "service_job" and .events[0].payload.payload_ref == "msg:sj-result-1"' \
    "$base/examples/cross-path/poll_cycle_outcome.job_complete.json" >/dev/null
echo "    [ok] cross-path registration adds start position; event is job_complete"

echo "    Fixture hygiene..."
hygiene_scan "$base"
echo "    [ok] fixture hygiene"

echo "    [ok] agent-wait control battery passed"
