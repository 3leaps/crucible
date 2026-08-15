#!/usr/bin/env sh
# Normative checks for contract: agent-wait/v0 — rules JSON Schema cannot prove.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils, date — baseline
#   jq — structural inspection of contract fixtures (same house pattern as
#        validate-review-journal-set.sh)
#   goneat is not invoked here; schema validation is the caller's job.
#
# Usage: validate-agent-wait-normative.sh <file-or-directory>
# Exit 0 when every applicable rule holds. On failure prints
#   normative_reason: <code>
# and exits 1.
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: validate-agent-wait-normative.sh <file-or-directory>" >&2
    exit 2
fi

target=$1
tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT
index="$tmpd/index.ndjson"

fail() {
    printf 'normative_reason: %s\n' "$1" >&2
    exit 1
}

ts_epoch() {
    date -u -d "$1" +%s
}

collect_json() {
    if [ -f "$target" ]; then
        printf '%s\n' "$target"
    elif [ -d "$target" ]; then
        find "$target" -type f -name '*.json' | sort
    else
        echo "    [!!] missing target: $target" >&2
        exit 1
    fi
}

: >"$index"
for f in $(collect_json); do
    jq -c --arg path "$f" '. + {_path: $path}' "$f" >>"$index"
done

# --- per-message rules ---
while IFS= read -r row; do
    [ -n "$row" ] || continue
    mt=$(printf '%s' "$row" | jq -r '.message_type')

    case "$mt" in
        live_wait_request | poll_cycle_request)
            run=$(printf '%s' "$row" | jq -r '.run_deadline')
            logical=$(printf '%s' "$row" | jq -r '.logical_deadline')
            if [ "$(ts_epoch "$run")" -gt "$(ts_epoch "$logical")" ]; then
                fail deadline_ordering
            fi
            ;;
    esac

    if [ "$mt" = "poll_cycle_outcome" ]; then
        kind=$(printf '%s' "$row" | jq -r '.outcome_kind')
        events_n=$(printf '%s' "$row" | jq -r '.events | length')
        complete=$(printf '%s' "$row" | jq -r '.coverage_complete')
        completed=$(printf '%s' "$row" | jq -r '.completed_at')
        logical=$(printf '%s' "$row" | jq -r '.logical_deadline')
        dirty=$(printf '%s' "$row" | jq -r '
            [.arms[] | select(.required == true) | select(.status == "outage" or .status == "cursor_uncertain" or .degraded == true)] | length
        ')
        req_no_change=$(printf '%s' "$row" | jq -r '
            ([.arms[] | select(.required == true)] | length) as $n
            | ([.arms[] | select(.required == true and .status == "no_change" and .degraded == false)] | length) as $ok
            | if $n > 0 and $n == $ok then "true" else "false" end
        ')
        req_complete=$(printf '%s' "$row" | jq -r '
            ([.arms[] | select(.required == true)] | length) as $n
            | ([.arms[] | select(.required == true and .degraded == false and .status != "outage" and .status != "cursor_uncertain")] | length) as $ok
            | if $n > 0 and $n == $ok then "true" else "false" end
        ')

        if [ "$dirty" -gt 0 ] && { [ "$kind" = "no_change" ] || [ "$kind" = "logical_deadman" ]; }; then
            fail outage_not_clean
        fi

        if [ "$kind" = "no_change" ]; then
            if [ "$events_n" -ne 0 ] || [ "$complete" != "true" ] || [ "$req_no_change" != "true" ] ||
                [ "$(ts_epoch "$completed")" -ge "$(ts_epoch "$logical")" ]; then
                fail no_change_invariants
            fi
        fi

        if [ "$kind" = "logical_deadman" ]; then
            if [ "$events_n" -ne 0 ] || [ "$complete" != "true" ] || [ "$req_complete" != "true" ] ||
                [ "$(ts_epoch "$completed")" -lt "$(ts_epoch "$logical")" ]; then
                fail deadman_invariants
            fi
        fi
    fi
done <"$index"

# --- set rules ---
req_arms=$(jq -s -c '[.[] | select(.message_type == "poll_cycle_request") | .required_arms] | add // []' "$index")
if [ "$(printf '%s' "$req_arms" | jq 'length')" -gt 0 ]; then
    jq -s --argjson req "$req_arms" '
        [.[] | select(.message_type == "poll_cycle_outcome" and .coverage_complete == true)]
        | if length == 0 then empty
          else
            .[] | ((.arms | map(.arm_id)) as $have
              | ($req | unique | map(select(. as $a | ($have | index($a) | not)))) )
          end
    ' "$index" >"$tmpd/missing_arms.json"
    if [ -s "$tmpd/missing_arms.json" ] && [ "$(jq -s 'add | length' "$tmpd/missing_arms.json")" -gt 0 ]; then
        fail coverage_cardinality
    fi
fi

if jq -s -e '[.[] | select(.message_type == "poll_cycle_outcome")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "poll_cycle_ack")] | length >= 1' "$index" >/dev/null; then
    bad=$(jq -s '
        ([.[] | select(.message_type == "poll_cycle_outcome")] | last) as $o
        | ([.[] | select(.message_type == "poll_cycle_ack")] | last) as $a
        | ($o.retained_event_ids + [$o.retained_through.value]) as $kept
        | (
            ($a.committed_anchor.value as $c | ($kept | index($c) | not))
            or
            ([ $a.acked_event_ids[] | select(. as $e | ($kept | index($e) | not)) ] | length > 0)
          )
    ' "$index")
    if [ "$bad" = "true" ]; then
        fail ack_past_unretained
    fi
fi

if jq -s -e '[.[] | select(.message_type == "poll_cycle_outcome")] | length >= 2' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "poll_cycle_ack")] | length == 0' "$index" >/dev/null; then
    advanced=$(jq -s '
        ([.[] | select(.message_type == "poll_cycle_outcome")] | sort_by(.created_at)) as $os
        | $os[0] as $first
        | $os[-1] as $last
        | ($first.events | map(.event_id)) as $ids
        | ($last.events | map(.event_id)) as $later
        | ($ids | length > 0)
          and (($ids - $later) | length > 0)
          and ($last.proposed_next_anchor.value != $first.proposed_next_anchor.value)
    ' "$index")
    if [ "$advanced" = "true" ]; then
        fail silent_cursor_advance
    fi
fi

if jq -s -e '[.[] | select(.message_type == "registration_set")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "poll_cycle_request" or .message_type == "live_wait_request")] | length >= 1' "$index" >/dev/null; then
    crossed=$(jq -s '
        ([.[] | select(.message_type == "registration_set")] | last.registration_revision) as $rev
        | [.[] | select(.message_type == "poll_cycle_request" or .message_type == "live_wait_request")
            | select(.registration_revision != $rev)] | length > 0
    ' "$index")
    if [ "$crossed" = "true" ]; then
        fail revision_cross
    fi
fi
