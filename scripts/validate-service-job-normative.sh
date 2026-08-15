#!/usr/bin/env sh
# Normative checks for contract: service-job/v0 — rules JSON Schema cannot prove.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils, sha256sum — baseline
#   jq — structural inspection of contract fixtures (same house pattern as
#        validate-review-journal-set.sh)
#   python3 — subject-matter runtime for portable RFC3339 instants
#             (scripts/rfc3339-instant.py) and RFC 8785 JobSpec digest
#             verification before any semantic use
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

if ! command -v python3 >/dev/null 2>&1; then
    echo "validate-service-job-normative.sh requires python3" >&2
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

collect_json() {
    if [ -f "$target" ]; then
        printf '%s\n' "$target"
    elif [ -d "$target" ]; then
        # Hash-order the files so directory listing cannot become protocol order.
        find "$target" -type f -name '*.json' | while IFS= read -r f; do
            printf '%s\t%s\n' "$(printf '%s' "$f" | sha256sum | awk '{print $1}')" "$f"
        done | sort | awk -F '\t' '{print $2}'
    else
        echo "    [!!] missing target: $target" >&2
        exit 1
    fi
}

: >"$index"
for f in $(collect_json); do
    case "$(basename "$f")" in
        interpretation.json) continue ;;
    esac
    jq -c --arg path "$f" '. + {_path: $path}' "$f" >>"$index"
done

# Recompute and constant-compare every submit JobSpec digest before semantic use.
while IFS= read -r row; do
    [ -n "$row" ] || continue
    mt=$(printf '%s' "$row" | jq -r '.message_type')
    [ "$mt" = "job_submit_request" ] || continue
    claimed=$(printf '%s' "$row" | jq -r '.job_spec_digest.value // empty')
    [ -n "$claimed" ] || fail job_spec_digest_mismatch
    printf '%s' "$row" | jq -c '.job_spec' >"$tmpd/job_spec.json"
    got=$(python3 scripts/rfc8785-canonicalize.py "$tmpd/job_spec.json" | sha256sum | awk '{print $1}')
    if [ "$got" != "$claimed" ]; then
        fail job_spec_digest_mismatch
    fi
    env_svc=$(printf '%s' "$row" | jq -r '.service_id')
    spec_svc=$(printf '%s' "$row" | jq -r '.job_spec.service_id')
    env_cat=$(printf '%s' "$row" | jq -r '.catalog_revision')
    spec_cat=$(printf '%s' "$row" | jq -r '.job_spec.catalog_revision')
    env_off=$(printf '%s' "$row" | jq -r '.offer_revision')
    spec_off=$(printf '%s' "$row" | jq -r '.job_spec.offer_revision')
    if [ "$env_svc" != "$spec_svc" ] || [ "$env_cat" != "$spec_cat" ] || [ "$env_off" != "$spec_off" ]; then
        fail job_spec_citation_mismatch
    fi
done <"$index"

# Cancel-accepted is not cancelled. An interpretation sidecar may not equate them.
if [ -d "$target" ] && [ -f "$target/interpretation.json" ]; then
    treated=$(jq -r '.treat_cancel_accepted_as // empty' "$target/interpretation.json")
    if [ "$treated" = "cancelled" ]; then
        fail cancel_accepted_as_cancelled
    fi
fi

# Catalog pagination pairs each response to its request_ref, not a global last.
if jq -s -e '[.[] | select(.message_type == "catalog_list_request")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "catalog_list_response")] | length >= 1' "$index" >/dev/null; then
    crossed=$(jq -s '
        [.[] | select(.message_type == "catalog_list_request")] as $qs
        | [.[] | select(.message_type == "catalog_list_response")] as $rs
        | [
            $rs[] as $r
            | ($qs | map(select(.message_id == $r.request_ref)) | .[0]) as $q
            | select($q != null)
            | ($q.catalog_revision != null) and ($q.catalog_revision != $r.catalog_revision)
          ]
        | any
    ' "$index")
    if [ "$crossed" = "true" ]; then
        fail pagination_revision_cross
    fi
fi

# Offer integrity pairs by JobSpec service + catalog revision + offer revision.
if jq -s -e '[.[] | select(.message_type == "service_offer")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 1' "$index" >/dev/null; then
    mismatch=$(jq -s '
        [.[] | select(.message_type == "service_offer")] as $offers
        | [
            .[] | select(.message_type == "job_submit_request") as $s
            | ($offers | map(select(
                .service_id == $s.job_spec.service_id
                and .catalog_revision == $s.job_spec.catalog_revision
                and .offer_revision == $s.job_spec.offer_revision
              )) | .[0]) as $o
            | select($o != null)
            | ($s.job_spec.offer_revision != $o.offer_revision
               or $s.job_spec.catalog_revision != $o.catalog_revision
               or $s.job_spec.service_id != $o.service_id)
          ]
        | any
    ' "$index")
    if [ "$mismatch" = "true" ]; then
        fail offer_revision_mismatch
    fi
    # A submit whose cited offer identity is present in the set but does not
    # match any offer is also a mismatch. Unrelated offers are ignored.
    dangling=$(jq -s '
        [.[] | select(.message_type == "service_offer")] as $offers
        | [
            .[] | select(.message_type == "job_submit_request") as $s
            | select(($offers | map(.service_id) | index($s.job_spec.service_id)) != null)
            | select(($offers | map(select(
                .service_id == $s.job_spec.service_id
                and .catalog_revision == $s.job_spec.catalog_revision
                and .offer_revision == $s.job_spec.offer_revision
              )) | length) == 0)
          ]
        | length > 0
    ' "$index")
    if [ "$dangling" = "true" ]; then
        fail offer_revision_mismatch
    fi
fi

# Pair each accepted receipt to its submit by submit_ref == message_id.
# Omitted backend may resolve only the offer's declared available local default.
if jq -s -e '[.[] | select(.message_type == "job_submit_request")] | length >= 1' "$index" >/dev/null &&
    jq -s -e '[.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] | length >= 1' "$index" >/dev/null; then
    default_mismatch=$(jq -s '
        [.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] as $ads
        | [.[] | select(.message_type == "job_submit_request")] as $subs
        | [.[] | select(.message_type == "service_offer")] as $offers
        | [
            $ads[] as $a
            | ($subs | map(select(.message_id == $a.submit_ref)) | .[0]) as $s
            | select($s != null and $s.job_spec.backend_ref == null)
            | ($offers | map(select(
                .service_id == $s.job_spec.service_id
                and .catalog_revision == $s.job_spec.catalog_revision
                and .offer_revision == $s.job_spec.offer_revision
              )) | .[0]) as $o
            | select($o != null)
            | ($o.backends | map(select(.default_local == true and .availability == "available" and .placement == "local"))) as $defaults
            | (
                ($defaults | length) != 1
                or (
                  $a.resolved_placement != "hosted"
                  and $a.resolved_backend_ref != $defaults[0].backend_ref
                )
              )
          ]
        | any
    ' "$index")
    if [ "$default_mismatch" = "true" ]; then
        fail local_default_resolution
    fi

    fallback=$(jq -s '
        [.[] | select(.message_type == "job_admission_receipt" and .admission == "accepted")] as $ads
        | [.[] | select(.message_type == "job_submit_request")] as $subs
        | [
            $ads[] as $a
            | ($subs | map(select(.message_id == $a.submit_ref)) | .[0]) as $s
            | select($s != null)
            | (($s.job_spec.placement == null) or ($s.job_spec.placement == "local"))
              and ($s.job_spec.backend_ref == null)
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
            | select($s != null and $s.job_spec.placement == "hosted")
            | ($offers | map(select(
                .service_id == $s.job_spec.service_id
                and .catalog_revision == $s.job_spec.catalog_revision
                and .offer_revision == $s.job_spec.offer_revision
              )) | .[0]) as $o
            | (
                ($s.egress_authorization_ref == null)
                or ($s.job_spec.backend_ref == null)
                or ($a.resolved_backend_ref != $s.job_spec.backend_ref)
                or ($a.resolved_placement != "hosted")
                or (
                    $o != null
                    and ($o.backends | map(select(.backend_ref == $s.job_spec.backend_ref and .placement == "hosted")) | length == 0)
                  )
              )
          ]
        | any
    ' "$index")
    if [ "$hosted_mismatch" = "true" ]; then
        fail hosted_backend_integrity
    fi
fi

# Unknown is scoped: original submit→unknown with no later scoped submit is fine.
# A later submit in the same actor+service+key scope before resolution is not.
if jq -s -e '[.[] | select(.message_type == "job_admission_receipt" and .admission == "unknown")] | length >= 1' "$index" >/dev/null; then
    jq -s -c '
        [.[] | select(.message_type == "job_submit_request")] as $subs
        | [.[] | select(.message_type == "job_admission_receipt" and .admission == "unknown")] as $unks
        | $unks[] as $u
        | ($subs | map(select(.message_id == $u.submit_ref)) | .[0]) as $orig
        | select($orig != null)
        | $subs[]
        | select(.message_id != $orig.message_id)
        | select(.actor_ref == $orig.actor_ref and .service_id == $orig.service_id and .idempotency_key == $orig.idempotency_key)
        | {unknown: $u.created_at, retry: .created_at}
    ' "$index" >"$tmpd/unknown_retry.ndjson"
    while IFS= read -r pair; do
        [ -n "$pair" ] || continue
        unk=$(printf '%s' "$pair" | jq -r '.unknown')
        retry=$(printf '%s' "$pair" | jq -r '.retry')
        compare_instants "$unk" "$retry"
        if [ "$_rel" -lt 0 ]; then
            fail unknown_admission_retry
        fi
    done <"$tmpd/unknown_retry.ndjson"
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
            | ($offers | map(select(
                .service_id == $s.job_spec.service_id
                and .catalog_revision == $s.job_spec.catalog_revision
                and .offer_revision == $s.job_spec.offer_revision
              )) | .[0]) as $o
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
            admitted: ["queued", "running", "cancel_requested", "cancelled", "failed", "expired"],
            queued: ["running", "cancel_requested", "cancelled", "failed", "expired"],
            running: ["succeeded", "failed", "cancel_requested", "cancelled", "partial", "expired"],
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
