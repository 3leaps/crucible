#!/usr/bin/env sh
# Normative checks for contract: agent-wait/v0 — rules JSON Schema cannot prove.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils, sha256sum — baseline
#   jq — structural inspection of contract fixtures (same house pattern as
#        validate-review-journal-set.sh)
#   python3 — subject-matter runtime for portable RFC3339 instants
#             (scripts/rfc3339-instant.py; no GNU/BSD date) and RFC 8785
#             registration-digest materialization
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

if [ ! -e "$target" ]; then
    echo "    [!!] missing target: $target" >&2
    exit 1
fi
if [ ! -r "$target" ]; then
    echo "    [!!] unreadable target: $target" >&2
    exit 1
fi
if [ ! -f "$target" ] && [ ! -d "$target" ]; then
    echo "    [!!] missing target: $target" >&2
    exit 1
fi

tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT
index="$tmpd/index.ndjson"
files="$tmpd/files.list"

if ! command -v python3 >/dev/null 2>&1; then
    echo "validate-agent-wait-normative.sh requires python3" >&2
    exit 2
fi

fail() {
    printf 'normative_reason: %s\n' "$1" >&2
    exit 1
}

# Sets _rel to -1, 0, or 1. Exits the checker immediately on an unparseable
# timestamp so comparisons never run on empty epoch values.
compare_instants() {
    _rel=$(python3 scripts/rfc3339-instant.py --compare "$1" "$2") || fail unparseable_timestamp
    case "$_rel" in
        -1 | 0 | 1) ;;
        *) fail unparseable_timestamp ;;
    esac
}

# Resolve the target in this shell. A missing or empty target must not
# become a successful zero-record pass via command substitution.
if [ -f "$target" ]; then
    printf '%s\n' "$target" >"$files"
else
    if ! find "$target" -type f -name '*.json' >"$tmpd/found.list"; then
        echo "    [!!] unreadable target: $target" >&2
        exit 1
    fi
    if [ ! -s "$tmpd/found.list" ]; then
        echo "    [!!] empty target: $target" >&2
        exit 1
    fi
    # Hash-order the files so directory listing cannot become protocol order.
    while IFS= read -r f; do
        printf '%s\t%s\n' "$(printf '%s' "$f" | sha256sum | awk '{print $1}')" "$f"
    done <"$tmpd/found.list" | sort | awk -F '\t' '{print $2}' >"$files"
fi

: >"$index"
while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ ! -r "$f" ]; then
        echo "    [!!] unreadable target: $f" >&2
        exit 1
    fi
    jq -c --arg path "$f" '. + {_path: $path}' "$f" >>"$index" || {
        echo "    [!!] malformed JSON: $f" >&2
        exit 1
    }
done <"$files"

if [ ! -s "$index" ]; then
    echo "    [!!] empty target: $target" >&2
    exit 1
fi

# --- per-message rules ---
while IFS= read -r row; do
    [ -n "$row" ] || continue
    mt=$(printf '%s' "$row" | jq -r '.message_type')

    case "$mt" in
        live_wait_request | poll_cycle_request)
            run=$(printf '%s' "$row" | jq -r '.run_deadline')
            logical=$(printf '%s' "$row" | jq -r '.logical_deadline')
            compare_instants "$run" "$logical"
            if [ "$_rel" -gt 0 ]; then
                fail deadline_ordering
            fi
            ;;
        registration_set)
            claimed=$(printf '%s' "$row" | jq -r '.registration_digest.value // empty')
            if [ -n "$claimed" ]; then
                printf '%s' "$row" | jq -c '.registrations' >"$tmpd/regs.json"
                got=$(python3 scripts/rfc8785-canonicalize.py "$tmpd/regs.json" | sha256sum | awk '{print $1}')
                if [ "$got" != "$claimed" ]; then
                    fail registration_digest_mismatch
                fi
            fi
            ;;
    esac

    if [ "$mt" = "poll_cycle_outcome" ] || [ "$mt" = "live_wait_outcome" ]; then
        kind=$(printf '%s' "$row" | jq -r '.outcome_kind')
        events_n=$(printf '%s' "$row" | jq -r '.events // [] | length')
        complete=$(printf '%s' "$row" | jq -r '.coverage_complete // empty')
        completed=$(printf '%s' "$row" | jq -r '.completed_at')
        logical=$(printf '%s' "$row" | jq -r '.logical_deadline // empty')
        has_arms=$(printf '%s' "$row" | jq -r 'has("arms")')
        dirty=0
        req_no_change=false
        req_complete=false
        if [ "$has_arms" = "true" ]; then
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
        fi

        if [ "$dirty" -gt 0 ] && { [ "$kind" = "no_change" ] || [ "$kind" = "logical_deadman" ]; }; then
            fail outage_not_clean
        fi

        if [ "$kind" = "no_change" ]; then
            compare_instants "$completed" "$logical"
            if [ "$events_n" -ne 0 ] || [ "$complete" != "true" ] || [ "$req_no_change" != "true" ] ||
                [ "$_rel" -ge 0 ]; then
                fail no_change_invariants
            fi
        fi

        if [ "$kind" = "logical_deadman" ]; then
            compare_instants "$completed" "$logical"
            if [ "$events_n" -ne 0 ] || [ "$complete" != "true" ] || [ "$req_complete" != "true" ] ||
                [ "$_rel" -lt 0 ]; then
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
    cross=$(jq -s '
        [.[] | select(.message_type == "poll_cycle_ack")] as $acks
        | [.[] | select(.message_type == "poll_cycle_outcome")] as $outs
        | [
            $acks[] as $a
            | ($outs | map(select(.message_id == $a.outcome_ref)) | .[0]) as $o
            | select($o != null)
            | ($a.committed_anchors // {}) as $ca
            | ($o.retained_through // {}) as $rt
            | ($a.retained_events // {}) as $ae
            | ($o.retained_events // {}) as $oe
            | [
                ($ca | keys[]) as $rid
                | select(
                    ($ca[$rid] != $rt[$rid])
                    and ([($rt | keys[]) as $oid | select($oid != $rid and $ca[$rid] == $rt[$oid])] | length > 0)
                  )
              ]
              + [
                ($ae | keys[]) as $rid
                | ($ae[$rid] // [])[] as $eid
                | select(
                    ([($oe | to_entries[]) | select(.key != $rid and (.value | index($eid) != null))] | length > 0)
                  )
              ]
          ]
        | add
        | length > 0
    ' "$index")
    if [ "$cross" = "true" ]; then
        fail cross_arm_commit
    fi
    bad=$(jq -s '
        [.[] | select(.message_type == "poll_cycle_ack")] as $acks
        | [.[] | select(.message_type == "poll_cycle_outcome")] as $outs
        | [
            $acks[] as $a
            | ($outs | map(select(.message_id == $a.outcome_ref)) | .[0]) as $o
            | select($o != null)
            | ($a.committed_anchors // {}) as $ca
            | ($o.retained_through // {}) as $rt
            | ($a.retained_events // {}) as $ae
            | ($o.retained_events // {}) as $oe
            | (
                ([($ca | keys[]) as $rid | select($ca[$rid] != $rt[$rid])] | length > 0)
                or ([($ae | keys[]) as $rid
                    | ($ae[$rid] // [])[]
                    | select(. as $e | (($oe[$rid] // []) | index($e) | not))] | length > 0)
              )
          ]
        | any
    ' "$index")
    if [ "$bad" = "true" ]; then
        fail ack_past_unretained
    fi
fi

if jq -s -e '[.[] | select(.message_type == "poll_cycle_outcome")] | length >= 2' "$index" >/dev/null; then
    starved=$(jq -s '
        [.[] | select(.message_type == "poll_cycle_outcome")]
        | group_by(.waiter_id)
        | map(
            sort_by(.created_at)
            | . as $os
            | ($os | map(.arms[] | select(.required == true) | .arm_id) | unique) as $arms
            | [
                $arms[] as $arm
                | select(
                    ($os | all(.arms | map(select(.arm_id == $arm)) | .[0].status == "deferred"))
                    and ($os | any(.arms | map(select(.required == true and .arm_id != $arm and .status == "events")) | length > 0))
                    and (($os | map(.next_fairness_cursor) | unique | length) == 1)
                  )
                | $arm
              ]
            | length
          )
        | add // 0
    ' "$index")
    if [ "$starved" -gt 0 ]; then
        fail fairness_starvation
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
          and (
            [(($first.proposed_next_anchors // {}) | keys[]) as $rid
              | select(($last.proposed_next_anchors[$rid].value // "") != ($first.proposed_next_anchors[$rid].value // ""))]
            | length > 0
          )
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

# Lease expiry requires reauthentication_required. Authn required needs a receipt
# or a reauth outcome. Bounds may be exceeded only on partial/coverage_degraded.
if jq -s -e '[.[] | select(.message_type == "registration_set")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "poll_cycle_outcome" or .message_type == "live_wait_outcome")] | length >= 1' "$index" >/dev/null; then
    jq -s -c '
        [.[] | select(.message_type == "registration_set")] as $sets
        | [.[] | select(.message_type == "poll_cycle_outcome" or .message_type == "live_wait_outcome")] as $outs
        | [.[] | select(.message_type == "poll_cycle_request" or .message_type == "live_wait_request")] as $reqs
        | {sets: $sets, outs: $outs, reqs: $reqs}
    ' "$index" >"$tmpd/aw_scope.json"

    authn=$(jq -r '
        .sets as $sets
        | .reqs as $reqs
        | .outs as $outs
        | [
            $sets[] as $s
            | select($s.authn_mode == "required")
            | select(($reqs | length) == 0 or ($reqs | any(.verification_receipt_ref == null)))
            | select($outs | any(.outcome_kind == "events" or .outcome_kind == "no_change" or .outcome_kind == "logical_deadman" or .outcome_kind == "partial"))
          ]
        | length > 0
    ' "$tmpd/aw_scope.json")
    if [ "$authn" = "true" ]; then
        fail authn_required
    fi

    jq -c '
        .sets[] as $s
        | .outs[] as $o
        | $s.registrations[] as $r
        | {lease: $r.lease_expires_at, completed: $o.completed_at, kind: $o.outcome_kind}
    ' "$tmpd/aw_scope.json" >"$tmpd/leases.ndjson"
    while IFS= read -r pair; do
        [ -n "$pair" ] || continue
        lease=$(printf '%s' "$pair" | jq -r '.lease')
        completed=$(printf '%s' "$pair" | jq -r '.completed')
        kind=$(printf '%s' "$pair" | jq -r '.kind')
        compare_instants "$lease" "$completed"
        if [ "$_rel" -lt 0 ] && [ "$kind" != "reauthentication_required" ]; then
            fail lease_reauth
        fi
    done <"$tmpd/leases.ndjson"

    bound=$(jq -r '
        [
            .sets[] as $s
            | .outs[] as $o
            | select($o.outcome_kind != "partial" and $o.outcome_kind != "coverage_degraded")
            | ($o.events // []) as $ev
            | (
                ([ $s.registrations[] as $r
                   | select(([$ev[] | select(.registration_id == $r.registration_id)] | length) > $r.bounds.max_events)
                 ] | length > 0)
                or (($ev | length) > $s.aggregate_limits.max_events)
              )
        ] | any
    ' "$tmpd/aw_scope.json")
    if [ "$bound" = "true" ]; then
        # Distinguish per-registration vs aggregate for the expected reason.
        reg_hit=$(jq -r '
            [
                .sets[] as $s
                | .outs[] as $o
                | select($o.outcome_kind != "partial" and $o.outcome_kind != "coverage_degraded")
                | ($o.events // []) as $ev
                | [ $s.registrations[] as $r
                    | select(([$ev[] | select(.registration_id == $r.registration_id)] | length) > $r.bounds.max_events)
                  ]
                | length > 0
            ] | any
        ' "$tmpd/aw_scope.json")
        if [ "$reg_hit" = "true" ]; then
            fail registration_bound
        fi
        fail aggregate_bound
    fi
fi
