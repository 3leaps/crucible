#!/usr/bin/env bash
# Controls for contract-check sharding: every contract check runs in exactly one
# shard, every control script is wired into a shard, and the Check workflow
# matrix runs every shard.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflow="${repo_root}/.github/workflows/check.yml"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

fail() {
    echo "error: $*" >&2
    exit 1
}

# Recipe lines a target would run, without running them. Shard targets share
# contract-tools, so only lines that run a check are compared.
recipe() {
    make -s -n -C "${repo_root}" "$@" BIN_DIR="${repo_root}/bin" |
        grep -E 'scripts/|goneat (validate|schema)' || true
}

read -r -a shards <<<"$(make -s -C "${repo_root}" contract-shards)"
[ "${#shards[@]}" -gt 0 ] || fail "contract-shards printed no shard ids"

: >"${tmp}/union"
for shard in "${shards[@]}"; do
    recipe "check-contracts-shard-${shard}" >"${tmp}/shard-${shard}"
    [ -s "${tmp}/shard-${shard}" ] || fail "shard ${shard} runs no checks"
    cat "${tmp}/shard-${shard}" >>"${tmp}/union"
done

# Reference set: the contract checks `make check` runs through lint-config,
# plus the schema and portability targets. check-contracts is defined as the
# shard union, so it cannot serve as its own reference.
recipe lint-schemas lint-config test-portability >"${tmp}/all"
sort "${tmp}/union" >"${tmp}/union.sorted"
sort "${tmp}/all" >"${tmp}/all.sorted"
if ! cmp -s "${tmp}/union.sorted" "${tmp}/all.sorted"; then
    diff "${tmp}/all.sorted" "${tmp}/union.sorted" >&2 || true
    fail "shard recipes differ from lint-schemas + lint-config + test-portability (check run twice or not at all)"
fi

# Each control script and every TypeScript tool is wired into exactly one shard.
for script in "${repo_root}"/scripts/test-*-controls.sh "${repo_root}"/scripts/test-*-controls.py "${repo_root}"/scripts/*.ts; do
    name="scripts/$(basename "${script}")"
    count="$(grep -cF "${name}" "${tmp}/union" || true)"
    [ "${count}" -eq 1 ] || fail "${name} runs in ${count} contract shards; want exactly 1"
done

for shard in "${shards[@]}"; do
    grep -Eq "^\.PHONY:.* check-contracts-shard-${shard}( |$)" "${repo_root}/Makefile" ||
        fail "check-contracts-shard-${shard} is not declared .PHONY"
done

# The workflow matrix lists exactly the Makefile shards.
matrix="$(sed -n 's/^ *shard: *\[\(.*\)\] *$/\1/p' "${workflow}" | tr -d ' ' | tr ',' ' ')"
[ "${matrix}" = "${shards[*]}" ] ||
    fail "Check workflow shard matrix [${matrix}] does not match CONTRACT_SHARDS [${shards[*]}]"

echo "[ok] contract shards cover every check exactly once (${#shards[@]} shards)"
