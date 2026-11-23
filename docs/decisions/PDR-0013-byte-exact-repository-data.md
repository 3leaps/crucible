---
id: "PDR-0013"
title: "Byte-exact repository data is declared and verified by Git"
status: "proposed"
date: "2026-11-23"
last_updated: "2026-11-23"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / adopting repositories' byte-exact data"
tags:
  - "process"
  - "ci"
  - "git"
  - "verification"
  - "cross-platform"
relates-to:
  - "EPR-0002 (verification of resolved state and discriminating negative controls)"
  - "PDR-0006 (shipping charter and POSIX shell baseline)"
---

# PDR-0013: Byte-Exact Repository Data Is Declared and Verified by Git

## Status

**Proposed.** Acceptance establishes a repository-data and CI practice for
adopting repositories, each from an explicit first covered revision. Filing this
record creates no estate-wide obligation and does not claim that any repository
conforms. **Crucible itself is not yet covered by this profile**; its adoption
is a separate reviewed change.

## Context

Windows GitHub Actions runners and many Windows developer installations check
out repositories with `core.autocrlf=true`. Any tracked file Git treats as text
(`text=auto` detects it, or no attribute says otherwise) arrives with CRLF line
endings. Anything that compares raw bytes — digests, golden files, corpora, test
vectors, schemas pinned by SHA-256, or signed/pinned trust material — can then
fail on Windows or pass while comparing different bytes.

A second, earlier loss occurs on commit: under `text=auto` (with or without
`eol=lf`), a deliberately authored CRLF fixture is normalized to LF on
`git add`. The committed blob is already altered, and every subsequent checkout
matches the altered blob exactly, so a checkout-only comparison cannot detect
the loss. In addition, `binary` (`-diff -merge -text`) does not unset `filter`,
`ident`, or `working-tree-encoding`, so a broader rule can still transform
marked paths.

This defect is not confined to repositories that run Windows CI: a repository
without Windows CI still ships converted bytes to every Windows consumer that
clones it.

## Decision

**An adopting repository declares its byte-exact paths in `.gitattributes` and
verifies both the effective Git attributes and raw checked-out bytes using Git
itself as the oracle.**

### Scope and rollout expectation

Adoption is staged per repository and records an explicit first covered
revision. Repositories that publish bytes consumers pin (schemas, corpora,
reference vectors) are expected to adopt first, and new corpus or fixture
repositories should declare their byte-exact paths before their first data
commit so CRLF fixtures are not normalized on `git add`.

### R1. Declare byte-exact paths and require the effective result

The adopting repository declares its byte-exact paths in the root
`.gitattributes`:

```gitattributes
/fixtures/** -text -filter -ident -working-tree-encoding
```

For every tracked file under those declared paths, the effective attributes Git
computes must have `text`, `filter`, `ident`, and `working-tree-encoding` all
**unset** (`unspecified` is not `unset`). Effective means as `git check-attr`
reports them, so nested tracked `.gitattributes` files that re-enable conversion
are caught. Because `git check-attr` prints `unset` both for an actually unset
attribute (`-text`) and for a literal string value (`text=unset`), the check
must also rule out ambiguous assigned values (`=unset`, `=set`, `=unspecified`)
and confirm `-text` through Git's EOL reporting (`git ls-files --eol`).

### R2. Verify with Git using two assertions

CI runs a check that binds the inventory and expected blob SHAs to the checked
commit (`HEAD`, refusing any staged difference between the index and `HEAD`
before reading the index) and asserts, for the designated inventory of
byte-exact files:

1. **Effective policy**: `git check-attr` reports `text`, `filter`, `ident`, and
   `working-tree-encoding` all `unset` for every selected file (R1), no tracked
   `.gitattributes` assigns `=unset`/`=set`/`=unspecified` to those four
   attributes, and `git ls-files --eol` confirms `attr/-text` for every
   selected file.
2. **Raw bytes**: every selected working-tree path is a regular non-symlink
   file and hashes with `git hash-object --no-filters` to its committed blob
   SHA in `HEAD`.

The check fails closed on a missing working file, a working-tree symlink
substitution, a staged difference against `HEAD`, an empty required pathspec,
any Git or hash error, or short output; enumerates tracked files with NUL-safe
output; and handles file modes explicitly (symlinks, submodules, and unmerged
entries are refused or explicitly declared, never skipped silently). Git is the
oracle for Git behavior; the check does not re-implement `.gitattributes`
parsing.

Where the check runs:

- Repositories supporting Windows or shipping byte-pinned artifacts to Windows
  consumers run the check in a real Windows CI job with `core.autocrlf=true` set
  explicitly **before checkout** (isolated to that job/checkout and recorded as
  the conversion-stress configuration), rather than relying on mutable runner
  defaults. Setting `core.autocrlf=true` after checkout does not exercise
  checkout conversion.
- A portable `core.autocrlf=true` clone probe (also set before checkout) on
  Linux or macOS supplements this check, but is not a claimed Windows execution.

### R3. Or canonicalize, and name the contract

Paths whose comparisons are semantic (parse, then canonicalize) may be exempt
from R1 and R2 only through a decision record that names:

- the exact paths;
- the allowed normalization;
- the parser or canonicalization profile;
- the consumers relying on it; and
- the evidence that the comparison is line-ending independent.

A canonical-JSON digest does not waive a raw-input fixture, an end-of-line test,
a signature, or another consumer's byte pin. Byte-exact and semantic subsets may
coexist in one repository.

### R4. No substitute workarounds

Setting `core.autocrlf=false` before checkout is not a substitute for a
discriminating check on the consumer path: it hides the conversion defect from
CI while leaving default clones exposed
([EPR-0002](EPR-0002-verification-gate-integrity.md)). Remove
`core.autocrlf=false` where it stands in for R2 (unrelated jobs need not be
disturbed).

### Precedence boundary

`.git/info/attributes` has higher precedence than in-tree `.gitattributes`
files; global (`core.attributesFile`) and system attributes have lower
precedence. Clean CI runners carry none of these external files. Because R2 runs
in clean CI, a contributor's local higher-precedence `.git/info/attributes` is
out of scope.

## Reference check

Under [PDR-0006](PDR-0006-shipping-charter.md) (Rule 2a and Rule 2b), a copyable
check snippet declares its invocation set and targets the POSIX `sh` baseline:
`sh`, `git`, `tr`, `wc`, `awk`, `mktemp`, `rm`, and `cat`. Git performs pathspec
enumeration (`-z`);
the reference check refuses, as an error rather than a skip, any selected path
containing a newline or starting with a double quote so line framing is safe by
construction, and fails closed on Git errors or short output.

```sh
#!/bin/sh
# Usage: check-byte-exact.sh PATHSPEC...
#   e.g. check-byte-exact.sh ':(glob)fixtures/**' ':(glob)manifests/**/*.jsonl'
# Exit 0: ok; exit 1: policy or byte mismatch; exit 2: refusal or tool error.
set -eu

die() { printf 'check-byte-exact: %s\n' "$*" >&2; exit 2; }
[ "$#" -gt 0 ] || die 'usage: check-byte-exact.sh PATHSPEC...'

tmp=$(mktemp -d) || die 'mktemp failed'
trap 'rm -rf "$tmp"' EXIT
trap 'exit 2' HUP INT TERM

git rev-parse --is-inside-work-tree > /dev/null 2>&1 || die 'not inside a Git work tree'
git rev-parse --verify HEAD > /dev/null 2>&1 || die 'HEAD does not exist'
git diff --cached --quiet --ita-visible-in-index || die 'index differs from HEAD; commit or unstage before checking'
git diff --quiet -- ':(glob)**/.gitattributes' '.gitattributes' || die 'working-tree .gitattributes differs from HEAD'
git ls-files --others -z -- ':(glob)**/.gitattributes' '.gitattributes' > "$tmp/untracked.attr" || die 'git ls-files --others failed'
[ ! -s "$tmp/untracked.attr" ] || die 'untracked .gitattributes present in working tree'

# Reject ambiguous =unset/=set/=unspecified assignments in tracked .gitattributes
# (git check-attr prints "unset" for both -text and text=unset).
ambig_rc=0
git grep -nE '(^|[[:space:]])(text|filter|ident|working-tree-encoding)=(unset|set|unspecified)([[:space:]]|$)' \
    HEAD -- ':(glob)**/.gitattributes' '.gitattributes' > "$tmp/ambig" 2> /dev/null || ambig_rc=$?
if [ "$ambig_rc" -eq 0 ]; then
    cat "$tmp/ambig" >&2
    die 'ambiguous attribute assignment (=unset/=set/=unspecified) in tracked .gitattributes'
elif [ "$ambig_rc" -gt 1 ]; then
    die 'git grep failed while checking tracked .gitattributes'
fi

for spec in "$@"; do
    git ls-files -z -- "$spec" > "$tmp/one" || die "git ls-files failed for $spec"
    [ -s "$tmp/one" ] || die "pathspec selects no tracked file: $spec"
done

git ls-files -s -z -- "$@" > "$tmp/ls.z" || die 'git ls-files failed'
[ "$(tr -cd '\n' < "$tmp/ls.z" | wc -c)" -eq 0 ] || die 'a selected path contains a newline'
tr '\0' '\n' < "$tmp/ls.z" > "$tmp/ls"

awk -v paths="$tmp/paths" -v shas="$tmp/shas" '
    {
        tab = index($0, "\t")
        if (tab == 0) { print "malformed ls-files record"; bad = 1; exit }
        split(substr($0, 1, tab - 1), meta, " ")
        path = substr($0, tab + 1)
        if (meta[3] != "0") { print "unmerged entry: " path; bad = 1; exit }
        if (meta[1] != "100644" && meta[1] != "100755") {
            print "not a regular file (mode " meta[1] "): " path; bad = 1; exit
        }
        if (substr(path, 1, 1) == "\"") { print "path starts with a double quote: " path; bad = 1; exit }
        print path > paths
        print meta[2] > shas
        n++
    }
    END { if (bad) exit 1; if (n == 0) { print "no files selected"; exit 1 } }
' "$tmp/ls" > "$tmp/refusal" || die "$(cat "$tmp/refusal")"
count=$(wc -l < "$tmp/paths" | tr -d ' ')

tr '\n' '\0' < "$tmp/paths" > "$tmp/paths.z"
git check-attr -z --stdin text filter ident working-tree-encoding \
    < "$tmp/paths.z" > "$tmp/attr.z" || die 'git check-attr failed'
tr '\0' '\n' < "$tmp/attr.z" > "$tmp/attr"
[ "$(wc -l < "$tmp/attr" | tr -d ' ')" -eq $((count * 12)) ] || die 'git check-attr returned the wrong number of fields'
awk '
    NR % 3 == 1 { path = $0 } NR % 3 == 2 { attr = $0 }
    NR % 3 == 0 && $0 != "unset" { printf "conversion not unset: %s: %s=%s\n", path, attr, $0; bad++ }
    END { exit bad ? 1 : 0 }
' "$tmp/attr" > "$tmp/attr.fail" && attr_ok=1 || attr_ok=0

git ls-files --eol -z -- "$@" > "$tmp/eol.z" || die 'git ls-files --eol failed'
tr '\0' '\n' < "$tmp/eol.z" > "$tmp/eol"
[ "$(wc -l < "$tmp/eol" | tr -d ' ')" -eq "$count" ] || die 'git ls-files --eol returned the wrong number of records'
awk '
    {
        tab = index($0, "\t")
        if (tab == 0) { print "malformed eol record"; bad++; next }
        meta = substr($0, 1, tab - 1)
        path = substr($0, tab + 1)
        if (meta !~ /attr\/-text([[:space:]]|$)/) {
            printf "eol attribute is not -text: %s (%s)\n", path, meta; bad++
        }
    }
    END { exit bad ? 1 : 0 }
' "$tmp/eol" > "$tmp/eol.fail" && eol_ok=1 || eol_ok=0

while IFS= read -r p; do
    cur=$p
    while :; do
        [ ! -L "$cur" ] || die "working-tree symlink not allowed: $cur"
        case "$cur" in
            */*) cur=${cur%/*} ;;
            *) break ;;
        esac
    done
    [ -f "$p" ] || die "missing or non-regular working-tree file: $p"
done < "$tmp/paths"

git hash-object --no-filters --stdin-paths < "$tmp/paths" > "$tmp/got" || die 'git hash-object failed'
[ "$(wc -l < "$tmp/got" | tr -d ' ')" -eq "$count" ] || die 'git hash-object returned the wrong number of hashes'
awk -v shas="$tmp/shas" -v got="$tmp/got" '
    { getline want < shas; getline have < got
      if (want != have) { print "changed on checkout: " $0; bad++ } }
    END { exit bad ? 1 : 0 }
' "$tmp/paths" > "$tmp/bytes.fail" && bytes_ok=1 || bytes_ok=0

cat "$tmp/attr.fail" "$tmp/eol.fail" "$tmp/bytes.fail"
if [ "$attr_ok" -eq 1 ] && [ "$eol_ok" -eq 1 ] && [ "$bytes_ok" -eq 1 ]; then
    echo "ok: $count byte-exact files are unconverted and match their committed bytes"
    exit 0
fi
exit 1
```

## Negative controls (EPR-0002)

Under [EPR-0002](EPR-0002-verification-gate-integrity.md), an adopting
implementation must carry executable negative controls that reach each assertion
and fail when that assertion is removed. At minimum, demonstrate failure on:

- an authored CRLF sample (and an LF sample) under the declared paths, including
  comparing independently authored CRLF sample bytes against the stored blob
  when `text=auto eol=lf` is active (detecting add-time normalization even when
  checkout still matches the altered blob);
- removing the root R1 rule, partial unset (e.g., `-text` alone), an ambiguous
  assigned value (`text=unset eol=lf -filter -ident -working-tree-encoding`),
  and a nested `.gitattributes` override re-enabling conversion;
- altered working-tree bytes, a missing file, an empty pathspec, and invocation
  outside a Git work tree;
- index-vs-`HEAD` and `.gitattributes` divergence: a staged byte edit, a
  staged-only file, an intent-to-add (`git add -N`) entry, a staged removal,
  and an unstaged or untracked working-tree `.gitattributes` change;
- refused inputs: a path containing a newline, a path starting with a double
  quote, a tracked symlink, a working-tree regular-to-symlink leaf substitution
  pointing to identical bytes, and a working-tree symlinked parent directory; and
- Git tool failures: `git ls-files --others` non-zero exit with empty stdout,
  `git check-attr` non-zero exit, short `git check-attr` output, and short
  `git hash-object` output.

Deleting the root rule alone does not discriminate for binary files or
already-CRLF fixtures; include an LF text sample in the negative controls.

A repository may retain a stricter local `.gitattributes` authoring validator
alongside R2 to catch latent conversion rules before any data commit exists.

## Consequences

Byte-exact files survive default Windows clones intact, and Windows CI observes
conversion defects instead of masking them with `core.autocrlf=false`. Adopting
repositories maintain an explicit path inventory in `.gitattributes` and run the
two-assertion Git check in CI.

## References

- [EPR-0002: Verification gate integrity](EPR-0002-verification-gate-integrity.md)
- [PDR-0006: Shipping charter](PDR-0006-shipping-charter.md)
- [CI/CD Baseline — Windows Runners](../operations/ci-baseline.md#windows-runners)
- [Windows Runner Gotchas — CRLF Line Endings](../knowledge/cicd/github-actions/windows-runners.md#crlf-line-endings)
- [Decision-record taxonomy](../repository/decision-records.md)

## Revision History

| Date       | Status Change | Summary                                                     | Updated By |
| ---------- | ------------- | ----------------------------------------------------------- | ---------- |
| 2026-11-23 | → proposed    | Declare and verify byte-exact repository data with Git      | devlead    |
