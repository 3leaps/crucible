#!/usr/bin/env sh
# Conformance battery for contract: service-job/v0.
#
# Declared invocation set (PDR-0006 Rule 2b):
#   sh, coreutils, find, sha256sum, cmp — baseline
#   goneat — subject-matter (JSON Schema validation the contract names)
#   jq — structural inspection of contract fixtures (house pattern)
#   python3 — subject-matter runtime for the stdlib-only RFC 8785
#             materializer (the contract names JCS; jq -S is not JCS)
#             and the fail-closed RFC3339 instant helper
#
# Asserts:
#   - every declared message kind has a golden example that validates
#   - schema-labeled baseline-* pass and reject-* fail schema validation
#   - set fixtures are schema-valid (except interpretation sidecars)
#   - normative baselines pass and reject-* fail with the expected reason
#   - schema pairs differ in exactly one field
#   - RFC 8785 official-style vectors (numbers, keys, escaping, rejects)
#   - U+2028/U+2029 stay raw UTF-8; duplicate members and lone surrogates fail
#   - checked-in JobSpec JCS bytes and SHA-256 match as an integration case
#   - jq -S is not the digest oracle
#   - JobSpec parameters validate against the referenced portable schema
#   - changing any digest-covered JobSpec component changes the digest
#   - cross-contract audio → submit/result → agent-wait job_complete path
#   - fixtures contain no credentials, raw tokens, or machine-local paths
set -eu

base="schemas/service-job/v0"
schema="$base/service-job-message.schema.json"
aw_schema="schemas/agent-wait/v0/agent-wait-message.schema.json"
da_schema="schemas/data-artifact/v0/artifact-descriptor.schema.json"

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
        *pagination-revision-cross*) echo pagination_revision_cross ;;
        *offer-revision-mismatch*) echo offer_revision_mismatch ;;
        *local-to-hosted-fallback*) echo local_to_hosted_fallback ;;
        *hosted-backend-mismatch* | *hosted-not-in-offer*) echo hosted_backend_integrity ;;
        *local-default-resolution*) echo local_default_resolution ;;
        *idempotency-conflict* | *idempotency-job-id-drift*) echo idempotency_conflict ;;
        *unknown-admission-retry*) echo unknown_admission_retry ;;
        *illegal-transition*) echo illegal_transition ;;
        *terminal-escape*) echo terminal_escape ;;
        *cancel-accepted-as-cancelled*) echo cancel_accepted_as_cancelled ;;
        *artifact-requirement*) echo artifact_requirement ;;
        *cancel-conflict*) echo cancel_idempotency_conflict ;;
        *state-version-regression*) echo state_version_regression ;;
        *tampered-job-spec* | *tampered-digest*) echo job_spec_digest_mismatch ;;
        *local-default-none* | *local-default-ambiguous*) echo local_default_resolution ;;
        *) echo unknown ;;
    esac
}

echo "    RFC3339 instant helper (shared with agent-wait)..."
python3 scripts/rfc3339-instant.py --self-test || {
    echo "    [!!] RFC3339 instant self-test failed" >&2
    exit 1
}
for bad in \
    "20260815T170000Z" \
    "2026-W33-6T17:00:00Z" \
    "2026-227T17:00:00Z" \
    "2026-08-15T17:00Z" \
    "2026-08-15T17:00:00+0000" \
    "2026-08-15 17:00:00Z" \
    "2016-12-31T23:59:60Z"; do
    if python3 scripts/rfc3339-instant.py --epoch "$bad" >/tmp/sj-ts.out 2>/tmp/sj-ts.err; then
        echo "    [!!] non-RFC3339 instant was accepted: $bad" >&2
        exit 1
    fi
done
echo "    [ok] RFC3339 profile; non-RFC3339 ISO and leap seconds fail closed"

echo "    Positive coverage (one golden per declared kind)..."
for kind in \
    catalog_list_request catalog_list_response service_describe_request service_offer \
    job_submit_request job_admission_receipt job_status_request job_status \
    job_result_request job_result job_cancel_request job_cancel_receipt service_job_error; do
    f="$base/examples/${kind}.example.json"
    [ -f "$f" ] || {
        echo "    [!!] missing golden for $kind: $f" >&2
        exit 1
    }
    goneat validate data --schema-file "$schema" --data "$f" >/dev/null
    echo "    [ok] golden: $f"
done

echo "    Extra goldens (frozen terminals, cancel admissions, not-ready)..."
for extra in \
    job_result.partial.example.json \
    job_result.expired.example.json \
    job_cancel_receipt.refused.example.json \
    job_cancel_receipt.unsupported.example.json \
    job_cancel_receipt.unknown.example.json \
    service_job_error.result_not_ready.example.json \
    service_job_error.offer_revision_mismatch.example.json \
    service_job_error.idempotency_conflict.example.json \
    service_job_error.unknown_admission.example.json \
    service_job_error.unauthorized.example.json \
    service_job_error.invalid_job_spec.example.json \
    service_job_error.backend_unavailable.example.json \
    service_job_error.cancel_unsupported.example.json \
    service_job_error.timeout.example.json \
    service_job_error.internal.example.json \
    job_status.unknown.example.json; do
    f="$base/examples/$extra"
    [ -f "$f" ] || {
        echo "    [!!] missing extra golden: $f" >&2
        exit 1
    }
    goneat validate data --schema-file "$schema" --data "$f" >/dev/null
    echo "    [ok] extra golden: $f"
done

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

echo "    Set fixtures..."
for d in "$base"/rejects/set/baseline-* "$base"/rejects/set/reject-*; do
    [ -d "$d" ] || continue
    for f in "$d"/*.json; do
        [ -f "$f" ] || continue
        case "$(basename "$f")" in
            interpretation.json) continue ;;
        esac
        goneat validate data --schema-file "$schema" --data "$f" >/dev/null || {
            echo "    [!!] set fixture is not schema-valid: $f" >&2
            exit 1
        }
    done
done
for d in "$base"/rejects/set/baseline-*; do
    [ -d "$d" ] || continue
    sh scripts/validate-service-job-normative.sh "$d" || {
        echo "    [!!] baseline set failed: $d" >&2
        exit 1
    }
    echo "    [ok] baseline set passes: $d"
done
for d in "$base"/rejects/set/reject-*; do
    [ -d "$d" ] || continue
    if sh scripts/validate-service-job-normative.sh "$d" >/tmp/sj-norm.out 2>/tmp/sj-norm.err; then
        echo "    [!!] set reject passed the normative check: $d" >&2
        exit 1
    fi
    got=$(sed -n 's/^normative_reason: //p' /tmp/sj-norm.err | head -n 1)
    want=$(expected_reason "${d##*/}")
    if [ "$got" != "$want" ]; then
        echo "    [!!] expected reason $want, got ${got:-<none>}: $d" >&2
        cat /tmp/sj-norm.err >&2
        exit 1
    fi
    echo "    [ok] rejected set ($got): $d"
done

echo "    Pair-distance invariant (schema pairs)..."
for f in "$base"/rejects/schema/reject-*.json; do
    [ -f "$f" ] || continue
    twin="$(dirname "$f")/baseline-${f##*/reject-}"
    if [ ! -f "$twin" ]; then
        case "${f##*/}" in
            reject-hosted-without-egress.json) twin="$(dirname "$f")/baseline-hosted-fields.json" ;;
            reject-observe-hint-start-position.json) twin="$(dirname "$f")/baseline-observe-hint.json" ;;
            reject-accepted-without-job-id.json) twin="$(dirname "$f")/baseline-accepted-job-id.json" ;;
            reject-succeeded-without-output.json) twin="$(dirname "$f")/baseline-succeeded-output.json" ;;
            reject-result-not-ready.json) twin="$(dirname "$f")/baseline-terminal-result.json" ;;
            reject-cli-field.json | reject-missing-idempotency-key.json) twin="$(dirname "$f")/baseline-job-spec.json" ;;
            reject-unknown-with-job-id.json) twin="$(dirname "$f")/baseline-unknown-admission.json" ;;
            reject-admission-missing-reason.json) twin="$(dirname "$f")/baseline-admission-reason.json" ;;
            reject-admission-missing-decided-at.json) twin="$(dirname "$f")/baseline-admission-decided-at.json" ;;
            reject-cancel-missing-reason.json) twin="$(dirname "$f")/baseline-cancel-reason.json" ;;
            *)
                echo "    [!!] reject has no baseline twin: $f" >&2
                exit 1
                ;;
        esac
    fi
    assert_pair_distance_one "$twin" "$f"
    echo "    [ok] pair distance 1: $f"
done

echo "    RFC 8785 official-style vectors..."
canon_dir="$base/canonicalization"
rfc_dir="$canon_dir/rfc8785"
tmpd=$(mktemp -d)
trap 'rm -rf "$tmpd"' EXIT
for stem in values unicode-keys numbers escaping line-separators; do
    python3 scripts/rfc8785-canonicalize.py "$rfc_dir/${stem}.input.json" >"$tmpd/${stem}.jcs"
    if ! cmp -s "$rfc_dir/${stem}.canonical.jcs" "$tmpd/${stem}.jcs"; then
        echo "    [!!] RFC 8785 vector $stem does not match checked-in canonical bytes" >&2
        echo "         expected: $(cat "$rfc_dir/${stem}.canonical.jcs")" >&2
        echo "         got:      $(cat "$tmpd/${stem}.jcs")" >&2
        exit 1
    fi
    echo "    [ok] RFC 8785 vector: $stem"
done
want_lsps=$(tr -d '[:space:]' <"$rfc_dir/line-separators.hex")
got_lsps=$(python3 -c 'import pathlib,sys; sys.stdout.write(pathlib.Path(sys.argv[1]).read_bytes().hex())' "$tmpd/line-separators.jcs")
if [ "$got_lsps" != "$want_lsps" ]; then
    echo "    [!!] U+2028/U+2029 hex $got_lsps != $want_lsps" >&2
    exit 1
fi
if [ "$got_lsps" = "225c75323032385c753230323922" ]; then
    echo "    [!!] U+2028/U+2029 were escaped as \\\\u2028\\\\u2029" >&2
    exit 1
fi
echo "    [ok] U+2028/U+2029 canonical UTF-8 bytes $want_lsps"
python3 -c '
import json, pathlib, struct, sys
from importlib.machinery import SourceFileLoader

jcs = SourceFileLoader("jcs", "scripts/rfc8785-canonicalize.py").load_module()
samples = json.loads(pathlib.Path("schemas/service-job/v0/canonicalization/rfc8785/ieee-samples.json").read_text())
for row in samples:
    bits = int(row["ieee_hex"], 16)
    value = struct.unpack("<d", struct.pack("<Q", bits))[0]
    got = jcs._encode_number(value)
    want = row["canonical"]
    if got != want:
        raise SystemExit("ieee %s -> %s != %s" % (row["ieee_hex"], got, want))
print("    [ok] RFC 8785 IEEE hex samples")
'
python3 -c '
import json, pathlib, sys
from importlib.machinery import SourceFileLoader

jcs = SourceFileLoader("jcs", "scripts/rfc8785-canonicalize.py").load_module()
cases = json.loads(pathlib.Path("schemas/service-job/v0/canonicalization/rfc8785/rejects.json").read_text())["cases"]
for case in cases:
    try:
        document = jcs.jcs_loads(case["json_text"])
        jcs.jcs_dumps(document)
    except (ValueError, json.JSONDecodeError):
        continue
    raise SystemExit("reject case %s was accepted" % case["name"])
probes = json.loads(pathlib.Path("schemas/service-job/v0/canonicalization/rfc8785/string-bytes.json").read_text())["cases"]
for case in probes:
    got = jcs.jcs_dumps(jcs.jcs_loads(case["json_text"])).encode("utf-8").hex()
    if got != case["canonical_hex"]:
        raise SystemExit("%s hex %s != %s" % (case["name"], got, case["canonical_hex"]))
    if got == case.get("rejected_helper_hex"):
        raise SystemExit("%s matched rejected helper hex" % case["name"])
print("    [ok] RFC 8785 reject cases (numbers, duplicates, lone surrogates)")
print("    [ok] RFC 8785 string-byte probes (U+2028/U+2029 unescaped)")
'
if python3 scripts/rfc8785-canonicalize.py >/dev/null 2>"$tmpd/dup.err" <<'JSON'; then
{"a":1,"a":2}
JSON
    echo "    [!!] duplicate object members were accepted" >&2
    exit 1
fi
echo "    [ok] CLI rejects duplicate object members"

echo "    RFC 8785 JobSpec integration vector..."
python3 scripts/rfc8785-canonicalize.py "$canon_dir/jobspec.input.json" >"$tmpd/got.jcs"
if ! cmp -s "$canon_dir/jobspec.canonical.jcs" "$tmpd/got.jcs"; then
    echo "    [!!] recomputed JCS does not match checked-in canonical bytes" >&2
    exit 1
fi
got_digest=$(sha256sum "$tmpd/got.jcs" | awk '{print $1}')
want_digest=$(tr -d '[:space:]' <"$canon_dir/jobspec.sha256")
if [ "$got_digest" != "$want_digest" ]; then
    echo "    [!!] JCS digest $got_digest != expected $want_digest" >&2
    exit 1
fi
# jq -S is not JCS: pretty output and compact -S -c must not be the oracle.
jq -S . "$canon_dir/jobspec.input.json" >"$tmpd/jq-S.json"
jq -S -c . "$canon_dir/jobspec.input.json" >"$tmpd/jq-Sc.json"
if cmp -s "$tmpd/jq-S.json" "$canon_dir/jobspec.canonical.jcs"; then
    echo "    [!!] vector does not distinguish jq -S from JCS" >&2
    exit 1
fi
if cmp -s "$tmpd/jq-Sc.json" "$canon_dir/jobspec.canonical.jcs"; then
    echo "    [!!] vector does not distinguish jq -S -c from JCS" >&2
    exit 1
fi
# Golden submit job_spec must hash to the same digest.
python3 -c '
import json, hashlib, pathlib, sys
sys.path.insert(0, "scripts")
from importlib.machinery import SourceFileLoader
jcs = SourceFileLoader("jcs", "scripts/rfc8785-canonicalize.py").load_module()
spec = json.loads(pathlib.Path("schemas/service-job/v0/examples/job_submit_request.example.json").read_text())["job_spec"]
digest = hashlib.sha256(jcs.jcs_dumps(spec).encode("utf-8")).hexdigest()
want = pathlib.Path("schemas/service-job/v0/canonicalization/jobspec.sha256").read_text().strip()
if digest != want:
    raise SystemExit("submit job_spec digest %s != %s" % (digest, want))
'
echo "    [ok] JobSpec integration digest $want_digest (jq -S is not the oracle)"

echo "    Portable parameters schema..."
jq '.job_spec.parameters' "$base/examples/job_submit_request.example.json" >"$tmpd/parameters.json"
goneat validate data --schema-file "$base/parameters/transcribe.parameters.schema.json" --data "$tmpd/parameters.json" >/dev/null
jq '. + {cli_args: ["--model", "local"]}' "$tmpd/parameters.json" >"$tmpd/parameters-cli.json"
if goneat validate data --schema-file "$base/parameters/transcribe.parameters.schema.json" --data "$tmpd/parameters-cli.json" >/dev/null 2>&1; then
    echo "    [!!] parameters schema accepted a CLI-only field" >&2
    exit 1
fi
echo "    [ok] transcribe parameters validate; CLI-only keys are rejected"

echo "    Digest-covered JobSpec components..."
python3 -c '
import copy, hashlib, json, pathlib, sys
from importlib.machinery import SourceFileLoader

jcs = SourceFileLoader("jcs", "scripts/rfc8785-canonicalize.py").load_module()
spec = json.loads(pathlib.Path("schemas/service-job/v0/canonicalization/jobspec.input.json").read_text())
base = hashlib.sha256(jcs.jcs_dumps(spec).encode("utf-8")).hexdigest()

def digest(document):
    return hashlib.sha256(jcs.jcs_dumps(document).encode("utf-8")).hexdigest()

mutated = copy.deepcopy(spec)
mutated["inputs"][0]["digest"]["value"] = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
if digest(mutated) == base:
    raise SystemExit("changing inputs digest did not change JobSpec digest")

mutated = copy.deepcopy(spec)
mutated["parameters"]["language"] = "es"
if digest(mutated) == base:
    raise SystemExit("changing parameters did not change JobSpec digest")

mutated = copy.deepcopy(spec)
mutated["outputs"][0]["role"] = "notes"
if digest(mutated) == base:
    raise SystemExit("changing outputs did not change JobSpec digest")

mutated = copy.deepcopy(spec)
mutated["deadline"] = "2026-08-15T18:00:00Z"
if digest(mutated) == base:
    raise SystemExit("changing deadline did not change JobSpec digest")

for field, value in (
    ("catalog_revision", "catrev-other"),
    ("offer_revision", "offerrev-other"),
    ("service_id", "svc:other"),
    ("requester_ref", "seat:other"),
):
    mutated = copy.deepcopy(spec)
    mutated[field] = value
    if digest(mutated) == base:
        raise SystemExit("changing %s did not change JobSpec digest" % field)

mutated = copy.deepcopy(spec)
mutated["backend_ref"] = "backend:hosted-a"
if digest(mutated) == base:
    raise SystemExit("adding backend_ref did not change JobSpec digest")

mutated = copy.deepcopy(spec)
mutated["placement"] = "hosted"
if digest(mutated) == base:
    raise SystemExit("adding placement did not change JobSpec digest")
'
echo "    [ok] each digest-covered JobSpec component changes the canonical digest"

echo "    Cross-contract audio → job → agent-wait path..."
goneat validate data --schema-file "$da_schema" --data "$base/examples/cross-path/audio.descriptor.json" >/dev/null
goneat validate data --schema-file "$schema" --data "$base/examples/job_submit_request.example.json" >/dev/null
goneat validate data --schema-file "$schema" --data "$base/examples/job_admission_receipt.example.json" >/dev/null
goneat validate data --schema-file "$schema" --data "$base/examples/job_result.example.json" >/dev/null
goneat validate data --schema-file "$aw_schema" --data "schemas/agent-wait/v0/examples/cross-path/registration_set.job_complete.json" >/dev/null
goneat validate data --schema-file "$aw_schema" --data "schemas/agent-wait/v0/examples/cross-path/poll_cycle_outcome.job_complete.json" >/dev/null
# Audio uses profile tokens + media_type; no data-artifact base-enum bump.
jq -e '
  .grains[0].kind | test("/")
' "$base/examples/cross-path/audio.descriptor.json" >/dev/null
jq -e '
  .representations[0].media_type == "audio/wav"
  and (.representations[0].format | test("/"))
  and (.representations[0].role | test("/"))
' "$base/examples/cross-path/audio.descriptor.json" >/dev/null
# observe_hint has no start position; the consumer registration supplies it.
jq -e '
  .observe_hint | (has("start_anchor") or has("baseline_policy")) | not
' "$base/examples/job_admission_receipt.example.json" >/dev/null
jq -e '
  .registrations[0]
  | (has("start_anchor") or has("baseline_policy"))
  and ((has("start_anchor") and has("baseline_policy")) | not)
  and .method_id == "job_complete"
  and .subject_kind == "service_job"
  and .subject_id == "job:transcribe-1"
' "schemas/agent-wait/v0/examples/cross-path/registration_set.job_complete.json" >/dev/null
jq -e '
  (.events | length) == 1
  and .events[0].event_id == "evt:job-complete-1"
  and .events[0].payload.payload_ref == "msg:sj-result-1"
' "schemas/agent-wait/v0/examples/cross-path/poll_cycle_outcome.job_complete.json" >/dev/null
echo "    [ok] cross-path: audio profile → submit/result → one job_complete waiter"

echo "    Fixture hygiene..."
hygiene_scan "$base"
echo "    [ok] fixture hygiene"

echo "    [ok] service-job control battery passed"
