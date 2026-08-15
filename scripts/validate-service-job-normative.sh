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

# Pair each accepted receipt to its submit by submit_ref == message_id.
# Omitted backend may resolve only the offer's declared available local default.
if jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] | length >= 1' "$index" >/dev/null; then
    fallback=$(jq -s '
        [.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] as $ads
        | [.[] | select(.message_type == "job_submit_request")] as $subs
        | [
            $ads[] as $a
            | ($subs | map(select(.message_id == $a.submit_ref)) | .[0]) as $s
            | select($s != null)
            | (($s.placement == null) or ($s.placement == "local"))
              and ($s.backend_ref == null)
              and ($a.resolved_placement == "hosted")
          ]
        | any
    ' "$index")
    if [ "$fallback" = "true" ]; then
        fail local_to_hosted_fallback
    fi

    hosted_mismatch=$(jq -s '
        [.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] as $ads
        | [.[] | select(.message_type == "job_submit_request")] as $subs
        | [.[] | select(.message_type == "service_offer")] as $offers
        | [
            $ads[] as $a
            | ($subs | map(select(.message_id == $a.submit_ref)) | .[0]) as $s
            | select($s != null and $s.placement == "hosted")
            | ($offers | map(select(.offer_revision == $s.offer_revision)) | .[0]) as $o
            | (
                ($s.egress_authorization_ref == null)
                or ($s.backend_ref == null)
                or ($a.resolved_backend_ref != $s.backend_ref)
                or ($a.resolved_placement != "hosted")
                or (
                    $o != null
                    and ($o.backends | map(select(.backend_ref == $s.backend_ref and .placement == "hosted")) | length == 0)
                  )
              )
          ]
        | any
    ' "$index")
    if [ "$hosted_mismatch" = "true" ]; then
        fail hosted_backend_integrity
    fi

    default_mismatch=$(jq -s '
        [.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] as $ads
        | [.[] | select(.message_type == "job_submit_request")] as $subs
        | [.[] | select(.message_type == "service_offer")] as $offers
        | [
            $ads[] as $a
            | ($subs | map(select(.message_id == $a.submit_ref)) | .[0]) as $s
            | select($s != null and $s.backend_ref == null)
            | ($offers | map(select(.offer_revision == $s.offer_revision)) | .[0]) as $o
            | select($o != null)
            | ($o.backends | map(select(.default_local == true and .availability == "available" and .placement == "local")) | .[0]) as $d
            | $d != null and $a.resolved_backend_ref != $d.backend_ref
          ]
        | any
    ' "$index")
    if [ "$default_mismatch" = "true" ]; then
        fail local_default_resolution
    fi
fi

# Unknown is scoped: original submit→unknown with no later scoped submit is fine.
# A later submit in the same actor+service+key scope before resolution is not.
if jq -s -e '[.[] | select(.message_type == "job_admission_receipt" and .admission == "unknown")] | length >= 1' "$index" >/dev/null; then
    unknown_retry=$(jq -s '
        [.[] | select(.message_type == "job_submit_request")] as $subs
        | [.[] | select(.message_type == "job_admission_receipt" and .admission == "unknown")] as $unks
        | [
            $unks[] as $u
            | ($subs | map(select(.message_id == $u.submit_ref)) | .[0]) as $orig
            | select($orig != null)
            | [
                $subs[]
                | select(.message_id != $orig.message_id)
                | select(.actor_ref == $orig.actor_ref and .service_id == $orig.service_id and .idempotency_key == $orig.idempotency_key)
                | select(.created_at > $u.created_at)
              ]
            | length > 0
          ]
        | any
    ' "$index")
    if [ "$unknown_retry" = "true" ]; then
        fail unknown_admission_retry
    fi
fi

# Scoped idempotency: actor + service + key.
# Exact retry (same digest) must reuse job_id. Different digest is a conflict
# regardless of job_id. Unrelated scopes are not paired.
if jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 2' "$index" >/dev/null; then
    conflict=$(jq -s '
        [.[] | select(.message_type == "job_submit_request")] as $subs
        | [.[] | select(.message_type == "job_admission_receipt")] as $ads
        | [
            $subs[] as $s1
            | $subs[] as $s2
            | select($s1.message_id < $s2.message_id)
            | select($s1.actor_ref == $s2.actor_ref and $s1.service_id == $s2.service_id and $s1.idempotency_key == $s2.idempotency_key)
            | ($ads | map(select(.submit_ref == $s1.message_id and .admission == "accepted")) | .[0]) as $a1
            | ($ads | map(select(.submit_ref == $s2.message_id)) | .[0]) as $a2
            | select($a1 != null and $a2 != null)
            | (
                ($s1.job_spec_digest.value == $s2.job_spec_digest.value and $a2.admission == "accepted" and $a1.job_id != $a2.job_id)
                or ($s1.job_spec_digest.value != $s2.job_spec_digest.value and $a2.admission != "conflict")
              )
          ]
        | any
    ' "$index")
    if [ "$conflict" = "true" ]; then
        fail idempotency_conflict
    fi
fi

# Artifact requirements vs JobSpec inputs when an offer is present.
if jq -s -e '[.[] | select(.message_type == "service_offer")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 1' "$index" >/dev/null; then
    artifact_bad=$(jq -s '
        [.[] | select(.message_type == "service_offer")] as $offers
        | [.[] | select(.message_type == "job_submit_request")] as $subs
        | [
            $subs[] as $s
            | ($offers | map(select(.offer_revision == $s.offer_revision)) | .[0]) as $o
            | select($o != null)
            | $o.input_requirements[] as $req
            | ($s.job_spec.inputs | map(select(.role == $req.role))) as $got
            | (
                (($got | length) < $req.cardinality.min)
                or ($req.cardinality.max != null and ($got | length) > $req.cardinality.max)
                or ($req.profile != null and ($got | any(.profile != $req.profile)))
                or ($req.media_types != null and ($got | any(. as $g | $req.media_types | index($g.media_type) | not)))
                or ($req.digest_required == true and ($got | any(.digest == null)))
              )
          ]
        | any
    ' "$index")
    if [ "$artifact_bad" = "true" ]; then
        fail artifact_requirement
    fi
fi

# Cancel-request exact replay / conflict, scoped by actor + job + key.
if jq -s -e '[.[] | select(.message_type == "job_cancel_request")] | length >= 2' "$index" >/dev/null; then
    cancel_conflict=$(jq -s '
        [.[] | select(.message_type == "job_cancel_request")] as $reqs
        | [.[] | select(.message_type == "job_cancel_receipt")] as $rcs
        | [
            $reqs[] as $c1
            | $reqs[] as $c2
            | select($c1.message_id < $c2.message_id)
            | select($c1.actor_ref == $c2.actor_ref and $c1.job_id == $c2.job_id and $c1.idempotency_key == $c2.idempotency_key)
            | ($rcs | map(select(.cancel_request_ref == $c1.message_id)) | .[0]) as $r1
            | ($rcs | map(select(.cancel_request_ref == $c2.message_id)) | .[0]) as $r2
            | select($r1 != null and $r2 != null)
            | $r1.cancel_admission != $r2.cancel_admission
          ]
        | any
    ' "$index")
    if [ "$cancel_conflict" = "true" ]; then
        fail cancel_idempotency_conflict
    fi
fi

# Legal / terminal transitions across job_status messages for the same job_id.
# Order by monotonic state_version, not envelope created_at.
if jq -s -e '[.[] | select(.message_type == "job_status")] | length >= 2' "$index" >/dev/null; then
    version_bad=$(jq -s '
        [.[] | select(.message_type == "job_status")]
        | group_by(.job_id)
        | map(sort_by(.state_version)
            | . as $seq
            | [range(0; ($seq | length) - 1)
                | select($seq[.].state_version >= $seq[. + 1].state_version)]
            | length)
        | add // 0
    ' "$index")
    if [ "$version_bad" -gt 0 ]; then
        fail state_version_regression
    fi

    illegal=$(jq -s '
        def allowed:
          {
            admitted: ["queued", "running", "cancel_requested", "failed", "expired"],
            queued: ["running", "cancel_requested", "failed", "expired"],
            running: ["succeeded", "failed", "cancel_requested", "partial", "expired"],
            cancel_requested: ["cancelled", "succeeded", "failed", "running", "partial", "expired"],
            succeeded: [],
            failed: [],
            cancelled: [],
            partial: [],
            expired: [],
            unknown: ["admitted", "queued", "running", "cancel_requested", "succeeded", "failed", "cancelled", "partial", "expired"]
          };
        def terminal: ["succeeded", "failed", "cancelled", "partial", "expired"];
        [.[] | select(.message_type == "job_status")]
        | group_by(.job_id)
        | map(sort_by(.state_version)
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
        terminal=$(jq -s '
            def terminal: ["succeeded", "failed", "cancelled", "partial", "expired"];
            [.[] | select(.message_type == "job_status")]
            | group_by(.job_id)
            | map(sort_by(.state_version)
                | . as $seq
                | [range(0; ($seq | length) - 1)
                    | select(($seq[.].state as $s | terminal | index($s)) != null)
                    | select($seq[.].state != $seq[. + 1].state)]
                | length)
            | add // 0
        ' "$index")
        if [ "$terminal" -gt 0 ]; then
            fail terminal_escape
        fi
        fail illegal_transition
    fi
fi
