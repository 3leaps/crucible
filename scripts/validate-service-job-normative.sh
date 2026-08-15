#!/usr/bin/env sh
# Normative checks for contract: service-job/v0 — rules JSON Schema cannot prove.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils — baseline
#   jq — structural inspection of contract fixtures (same house pattern as
#        validate-review-journal-set.sh)
#
# Usage: validate-service-job-normative.sh <file-or-directory>
# Exit 0 when every applicable rule holds. On failure prints
#   normative_reason: <code>
# and exits 1.
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: validate-service-job-normative.sh <file-or-directory>" >&2
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

# Cancel-accepted is not cancelled. An interpretation sidecar may not equate them.
if [ -d "$target" ] && [ -f "$target/interpretation.json" ]; then
    treated=$(jq -r '.treat_cancel_accepted_as // empty' "$target/interpretation.json")
    if [ "$treated" = "cancelled" ]; then
        fail cancel_accepted_as_cancelled
    fi
fi

# Catalog pagination cannot silently cross revisions.
if jq -s -e '[.[] | select(.message_type == "catalog_list_request")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "catalog_list_response")] | length >= 1' "$index" >/dev/null; then
    crossed=$(jq -s '
        ([.[] | select(.message_type == "catalog_list_request")] | last) as $q
        | ([.[] | select(.message_type == "catalog_list_response")] | last) as $r
        | ($q.catalog_revision != null) and ($q.catalog_revision != $r.catalog_revision)
    ' "$index")
    if [ "$crossed" = "true" ]; then
        fail pagination_revision_cross
    fi
fi

# Offer / catalog revision integrity on submit.
if jq -s -e '[.[] | select(.message_type == "service_offer")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 1' "$index" >/dev/null; then
    mismatch=$(jq -s '
        ([.[] | select(.message_type == "service_offer")] | last) as $o
        | [.[] | select(.message_type == "job_submit_request")
            | select(.offer_revision != $o.offer_revision or .catalog_revision != $o.catalog_revision)]
        | length > 0
    ' "$index")
    if [ "$mismatch" = "true" ]; then
        fail offer_revision_mismatch
    fi
fi

# Local default must not resolve hosted. Hosted backend must match the submit ref.
if jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] | length >= 1' "$index" >/dev/null; then
    fallback=$(jq -s '
        ([.[] | select(.message_type == "job_submit_request")] | last) as $s
        | ([.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] | last) as $a
        | (($s.placement == null) or ($s.placement == "local"))
          and ($a.resolved_placement == "hosted")
    ' "$index")
    if [ "$fallback" = "true" ]; then
        fail local_to_hosted_fallback
    fi

    hosted_mismatch=$(jq -s '
        ([.[] | select(.message_type == "job_submit_request")] | last) as $s
        | ([.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] | last) as $a
        | ($s.placement == "hosted")
          and (
            ($s.egress_authorization_ref == null)
            or ($s.backend_ref == null)
            or ($a.resolved_backend_ref != $s.backend_ref)
            or ($a.resolved_placement != "hosted")
          )
    ' "$index")
    if [ "$hosted_mismatch" = "true" ]; then
        fail hosted_backend_integrity
    fi
fi

# Unknown admission must be resolved before another submit.
if jq -s -e '[.[] | select(.message_type == "job_admission_receipt" and .admission == "unknown")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 1' "$index" >/dev/null; then
    fail unknown_admission_retry
fi

# Idempotency: same digest + accepted => same job_id; different digest + same job_id accepted => conflict.
if jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 2' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] | length >= 2' "$index" >/dev/null; then
    conflict=$(jq -s '
        ([.[] | select(.message_type == "job_submit_request")] | sort_by(.created_at)) as $subs
        | ([.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] | sort_by(.created_at)) as $ads
        | $subs[0] as $s1 | $subs[-1] as $s2
        | $ads[0] as $a1 | $ads[-1] as $a2
        | ($s1.job_spec_digest.value != $s2.job_spec_digest.value)
          and ($a1.job_id == $a2.job_id)
    ' "$index")
    if [ "$conflict" = "true" ]; then
        fail idempotency_conflict
    fi
fi

# Legal / terminal transitions across job_status messages for the same job_id.
if jq -s -e '[.[] | select(.message_type == "job_status")] | length >= 2' "$index" >/dev/null; then
    illegal=$(jq -s '
        def allowed:
          {
            accepted: ["queued", "running", "cancel_requested", "failed"],
            queued: ["running", "cancel_requested", "failed"],
            running: ["succeeded", "failed", "cancel_requested"],
            cancel_requested: ["cancelled", "succeeded", "failed"],
            succeeded: [],
            failed: [],
            cancelled: []
          };
        [.[] | select(.message_type == "job_status")]
        | group_by(.job_id)
        | map(sort_by(.created_at)
            | . as $seq
            | [range(0; ($seq | length) - 1)
                | . as $i
                | select($seq[$i].state != $seq[$i+1].state)
                | select(($seq[$i+1].state as $n | (allowed[$seq[$i].state] | index($n)) | not))
              ]
            | length)
        | add // 0
    ' "$index")
    if [ "$illegal" -gt 0 ]; then
        # Distinguish terminal escape from other illegal hops using the first bad pair.
        terminal=$(jq -s '
            [.[] | select(.message_type == "job_status")]
            | sort_by(.created_at)
            | . as $seq
            | [range(0; ($seq | length) - 1)
                | select($seq[.].state == "succeeded" or $seq[.].state == "failed" or $seq[.].state == "cancelled")
                | select($seq[.].state != $seq[. + 1].state)]
            | length > 0
        ' "$index")
        if [ "$terminal" = "true" ]; then
            fail terminal_escape
        fi
        fail illegal_transition
    fi
fi
