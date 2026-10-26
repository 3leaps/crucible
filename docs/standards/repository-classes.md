---
title: "Repository Classes: prims, bolts, wits and voys"
description: "Pick a repo's class by who calls it; per-class MUST characteristics with observable checks, a repo declaration and a new-repo template; pressers as an adjacent class"
category: "standards"
status: "draft"
version: "0.1.0"
lastUpdated: "2026-10-25"
maintainer: "core-standards"
reviewers: ["devlead", "entarch", "cxotech"]
approvers: ["lead-maintainer"]
tags: ["repository", "taxonomy", "naming", "prims", "bindings", "conformance", "dependencies"]
content_license: "CC0"
supervised_by: "@3leapsdave"
relatedDocs:
  - "docs/decisions/ADR-0018-prims-multi-language-commitment.md"
  - "docs/repository/makefile-minimum.md"
  - "https://github.com/fulmenhq/crucible/blob/main/config/taxonomy/repository-categories.yaml"
  - "https://github.com/fulmenhq/crucible/blob/main/docs/architecture/fulmen-forge-workhorse-standard.md"
  - "https://github.com/fulmenhq/crucible/blob/main/docs/architecture/fulmen-forge-microtool-standard.md"
audience: "maintainers"
---

# Repository Classes

MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119. This spec adds a **class layer** over the fulmen
repository categories and forge standards. Where those already cover a requirement, they are linked, not repeated.

## 1. The test: who calls it?

Pick the class by its **primary caller**, not by language, size or how the brand sounds.

| Class | Name | Primary caller | Fulmen category (base) | Public examples |
|---|---|---|---|---|
| **prims** | `<noun>prims` | another program, **in-process** (import, FFI, binding) | `library` (a thin diagnostic CLI is a 3leaps extension of fulmen's "without executables") | sysprims, ipcprims, docprims, waitprims, yamlprims |
| **bolt** | `<noun>bolt` | a human or agent running **one command** that does one thing and returns | `cli` | refbolt |
| **wit** | `<noun>wit` | an operator or automation that relies on the tool's **know-how for one job** | `microtool` while CLI-only; `cli` once it adds a daemon, exported package or endpoint (§6) | spanwit, gearwit |
| **voy** | `<noun>voy` | **other actors** who submit work and **wait on it** through a long-running service | `workhorse` (or `service`) | chanvoy |
| presser *(adjacent)* | `<subject>presser` | maintainers and CI qualifying a subject; **never a production caller** | `cli` | none public yet |

A repo has exactly one class. A thin CLI over a prim does not make it a bolt. A one-shot mode of a voy does not make it a
bolt. Unsuffixed operator CLIs are outside these classes. Choose unsuffixed on its merits, never to dodge a class decision.

## 2. Repo declaration

Every classed repo MUST carry `.fulmen/repo.yaml`. Its schema is planned at
`schemas/taxonomy/v0/repo-declaration.schema.json`. Until that schema and a checker ship, the declaration is a
manual convention: a reviewer reads the file against the shape below, and nothing executes a block on it (§9).

```yaml
# .fulmen/repo.yaml: what this repo claims to be. The class check validates against this file.
schema: "contract:taxonomy/v0/repo-declaration.schema.json"
class: prims            # prims | bolt | wit | voy | presser
profile: B              # prims only: A (Rust core) | B (dual Go + Rust)
profile_status: bootstrapping   # B only: bootstrapping (operating tree named in README) | locked
leaf: false             # prims only: true = depends on no other prim, enforced by a CI dependency check (§4.1)
category: library       # fulmen repository-categories key; MUST equal .fulmen/app.yaml metadata.repository_category if present
env_prefix: EXAMPLEPRIMS_
umbrella_prefix: null   # optional, e.g. LANYTE_ for family-shared variables only
surfaces: [library, cli]            # any of: library, cli, daemon, pane, tui, http
bindings: {rust: shipped, go: shipped, typescript: planned, python: planned}   # prims only
extensions:             # anything beyond the class or fulmen base; each one is named and justified
  - id: go-mmap-reader
    scope: go-only
    reason: "capability only Go's runtime provides here"
```

`.fulmen/` is used because fulmen app identity (`.fulmen/app.yaml`) already lives there. `.crucible/` is not used: it
holds generated SSOT sync metadata in consumer repos.

## 3. Common MUST characteristics (all classes)

| # | MUST | Observable check |
|---|---|---|
| C1 | Declare the class | `.fulmen/repo.yaml` validates; the name suffix matches `class` |
| C2 | VERSION is the single version source | root `VERSION` is bare semver (no `v`); `make version` prints it; Cargo/npm/PyPI/embedded versions equal it |
| C3 | Env vars use `<NAME>_` | every env var name read in source starts with `env_prefix` or the declared `umbrella_prefix` |
| C4 | Minimum Make targets | `make -n` succeeds for the targets in `docs/repository/makefile-minimum.md` |
| C5 | Any CLI separates data and diagnostics, and offers JSON | `<bin> version --extended` exits 0; `<bin> <verb> --format json 2>/dev/null` parses and validates against `schemas/` |
| C6 | Go module root | if the repo contains a Go module that consumers import, `go.mod` is at the repo root and its module path is the repo URL, so one `VERSION` and one `vX.Y.Z` tag resolve (fulmen ADR-0009). A nested `go.mod` is flagged. Repos that have **already tagged** a nested Go module (a cgo `bindings/go/<name>` module beside a root module, or a pure-Go tree under `go/<pkg>` with its own tag prefix) keep that layout as a declared extension (`scope: legacy-go-module`) until their migration is decided; C6 does not block their releases in the meantime. The exception does not apply to an untagged repo: a Profile B prim that has not yet tagged puts its Go tree at the root before its first tag, while the move is cheap |
| C7 | Signed release | *(pre-release only)* `CHANGELOG.md`, `RELEASE_NOTES.md` and `RELEASE_CHECKLIST.md` present; the tag is annotated and signed (`git tag -v`); assets carry checksums, a detached signature and an SBOM |
| C8 | No secrets in the repo | no tracked `.env*` other than `.env.example`; the secret scan passes |

SHOULD (guidance, not checked): `doctor` and `docs list|show` from embedded, generated docs; exit codes and signals as
in the fulmen helper libraries; `LIFECYCLE_PHASE`.

## 4. prims: contract-first libraries with a multi-language commitment (normative)

A prims repo is a library whose public, versioned **contract** (schemas, documented semantics, conformance vectors) is
the product. Programs call it in-process. A CLI MAY exist only as a thin diagnostic surface over the same library. It is
never a second implementation. Every prim MUST declare a commitment to **Rust, Go, TypeScript and Python** consumers.
`bindings` in `.fulmen/repo.yaml` marks each as `shipped` or `planned`; a `planned` binding has its package name
reserved and named in the README. A prim with planned bindings is conformant; a prim with no stated path for one of the
four is not.

**Profile A: Rust core (default).** One Rust core. Go uses cgo over the prims JSON C-ABI (error code return, JSON
string out, thread-local last error, caller-freed strings, options as JSON), with prebuilt static libraries per platform.
TypeScript uses napi-rs. Python uses **PyO3/maturin**. All bindings come from the core and MUST NOT re-implement logic.
Choose A whenever consumers can live with cgo.

**Profile B: dual implementation.** Choose B when pure Go is required (no cgo). Use ONE repo with **locked parallel
native implementations** in pure Go and Rust, under the same contract, docs and decision records, passing one shared
conformance suite. A language-only capability is allowed only as a declared **extension** (§2), and it MUST NOT change
shared behaviour. TypeScript (napi-rs) and Python (PyO3/maturin) come from the Rust implementation. Both implementations
share **one version and one tag** (C6). Layout: root `go.mod` + Go packages, `crates/`, `conformance/`
(language-neutral vectors) and `contract/` (pinned crucible schemas). The first Profile B prim is a planned record-store
prim implementing `durable-record/v1`.

A Profile B prim bootstraps one tree at a time. Until both native trees pass the shared suite, the repo declares
`profile_status: bootstrapping` with the operating tree named, and only the operating tree is graded against
`conformance/`. During bootstrap the contract pin and the vectors are still shared, vector expected outputs are
authored as data (never snapshotted from the operating tree), and the second tree is scaffolded and marked planned.
Once both trees operate, the repo flips to `profile_status: locked` and the lockstep rule applies: a contract or
behaviour change lands only with both implementations and the shared tests changed **in the same PR**. The flip is a
release-notes entry, not a silent change.

| # | MUST | Observable check |
|---|---|---|
| P1 | Four-language commitment | `bindings` in repo.yaml lists rust, go, typescript and python as `shipped` or `planned`; each `planned` one has a reserved package name in the README |
| P2 | A: bindings generated from the core | `ffi/` has a C header; TS `package.json` builds with napi-rs; `pyproject.toml` has `build-backend = "maturin"` |
| P3 | B: shared conformance | `conformance/` exists; CI runs it under every operating tree; once `profile_status: locked`, CI runs both `go test` and `cargo test` and a PR changing `contract/` or `conformance/` touches both trees |
| P4 | Contract pin | `contract/PIN` (or equivalent) names the crucible schema version when a crucible contract is implemented |
| P5 | No daemon, no server | no `serve` verb; `surfaces` excludes daemon and http |
| P6 | Permissive licence, gated deps | LICENSE is MIT and/or Apache-2.0; `deny.toml` (Rust) or equivalent licence gate is present |
| P7 | Sibling prims as dependencies | at the first public release every prim dependency is a tagged version (exact-commit pins allowed before it); an exported-API scan per tree shows no sibling package or crate path (Go: exported identifiers and their import paths, e.g. `go doc -all` or `apidiff`; Rust: `cargo public-api`); a Profile B Go tree depends only on cgo-free Go modules; any per-tree gap is an `extensions` entry and an explicit `unsupported` vector; a `leaf: true` prim's dependency check passes; the prim graph has no cycle (§4.1) |

MUST NOT (stated, not mechanically checked): hold application policy, recipes, scheduling or operations; expose backend
or third-party types in the contract.

### 4.1 Depending on another prim

A prim MAY depend on a sibling prim. Reuse is the point of the family; a second implementation of a primitive that a
sibling already provides is the failure this class exists to prevent. Four rules keep the dependency honest:

1. **Pinned and public first.** At the dependent's first public release and after, the dependency is a tagged
   release of the sibling, never a branch or an unpinned path, and the sibling MUST already be public. Before that
   release a dependent MAY pin a private sibling at an exact commit, recorded the same way as a contract pin
   (repository, commit, digest), so development on two unreleased prims can proceed. P7 checks the tag at release,
   not on every PR.
2. **No sibling types in the contract.** The dependent's public API, `contract/` and `conformance/` expose none of the
   sibling's implementation or package-specific types. For this rule a separately versioned sibling prim is third-party
   under the §4 MUST NOT. Wrap it; do not re-export it. Referencing the sibling's public algorithm, a neutral schema it
   also implements, or a byte-level expected result in language-neutral vectors is fine; those are contract, not types.
3. **Profile compatibility per tree.** A Profile B prim's pure-Go tree MAY depend only on Go modules that need no cgo.
   A Profile A sibling therefore serves the Rust tree only. When the Go tree needs the same capability, either the
   sibling grows a pure-Go tree (becomes Profile B) or the dependent declares the gap for Go consumers. The dependent
   MUST NOT reimplement the sibling's logic in Go to close the gap. A declared gap is a per-tree capability
   difference: the shared vectors test the common semantics in both trees and test the gap as an explicit
   `unsupported` refusal on the tree that lacks it. They never grade one tree against behaviour only the other has, and
   the prim's declared profile or capability report advertises the difference. The gap is listed in `.fulmen/repo.yaml`
   `extensions` with the tree that has the capability (`scope: rust-only` or `go-only`), and that capability alone is
   scoped out of the cross-tree byte-identical requirement in P3. The rest of the suite still holds for both trees.
4. **Leaves and no cycles.** The prim dependency graph MUST be acyclic. A prim MAY declare `leaf: true`: it depends on
   no other prim, and a dependency check in its CI fails on any prim import. Foundation prims (canonical bytes,
   identity, digests) SHOULD be leaves; a leaf is what makes depending on a prim safe. A non-leaf prim allow-lists the
   siblings it uses, per tree, and the same check fails on any other prim import.

Example: a record store prim that adds an object-storage stratum depends on storageprims in its Rust tree. Its Go
tree ships the filesystem stratum and declares object storage as a Go-side gap until a pure-Go storageprims exists.
How that stratum is named on the wire belongs to the contract the prim implements (for durable-record, the
`runtime.stratum` field of its stratum profile), not to this standard.

## 5. bolts: one fast do

A CLI that does one thing, quickly, for humans and agents equally, then exits. It is Go or Rust, shipped as a single
host binary. It fails closed on uncertain permission, identity or output safety. A bolt MAY ship a library for its own CLI.
If another program needs that library, extract a prim. A bolt MAY run a **helper process that serves only its one
capability** (e.g. an OS-permission capture host), declared in `extensions`.

| # | MUST | Observable check |
|---|---|---|
| B1 | One capability | `<bin> --help` lists one capability verb (plus reserved `version`, `doctor`, `docs`) |
| B2 | No waiting, no daemon | no `serve` or `watch` verb; any helper process is declared in `extensions` with `scope: helper` |
| B3 | Pure stdout | C5 holds for the capability verb |

## 6. wits: single-purpose know-how

A wit is a **single-purpose know-how tool**. It owns one job with domain judgement (e.g. disk reclamation). It is
**CLI-first**, and it MAY add a daemon (`<name>d`), a pane or a TUI. All surfaces share one operation model. The
fulmen base depends on what it ships. A CLI-only wit is a fulmen `microtool` (single purpose, helper library, exit
codes, signals, `.fulmen/app.yaml`). fulmen's microtool category MUST NOT export packages, serve endpoints or be
imported by other repos, and a 3leaps extension cannot waive a base category's MUST NOT. So a wit that adds a daemon,
a local IPC endpoint or a client library for its own daemon declares `category: cli` in `.fulmen/repo.yaml` and keeps
the microtool discipline (single purpose, helper library, exit codes, signals) as the 3leaps wit rule. Those surfaces
are still declared `extensions` (W4). Neither case moves the wit to `workhorse`: that needs others queueing on it (§7).

| # | MUST | Observable check |
|---|---|---|
| W1 | Dry run by default | each mutating verb run without `--execute` exits 0, reports a plan and changes nothing |
| W2 | Surface parity | every surface in `surfaces` lists the same operation set (`<bin> ops --format json` = `<bin>d` `ops.list` = library operation table) |
| W3 | App identity | `.fulmen/app.yaml` validates; `env_prefix` equals repo.yaml |
| W4 | Extensions declared | any daemon, pane, TUI or exported package appears in `extensions` |

SHOULD: every mutation emits a receipt that separates requested, approved, attempted and observed.
MUST NOT: become a gateway others queue on (voy), become the library others build on (prim), or grow a second job.

## 7. voys: workhorse gateways and brokers

A long-running service that **other actors call and wait on**: a gateway, broker, plane or policy enforcement point. It
admits requests, applies policy, routes to drivers or workers and keeps durable receipts. Base: the fulmen workhorse
standard (`serve`, loopback-by-default host, health, version, metrics and request IDs for HTTP, control/data plane split).
A voy MAY offer a one-shot CLI mode. A voy that today ships CLI-plus-audit and has no `serve` is **catching up**: it holds
the class and owes V1 to V3 by its next minor release.

| # | MUST | Observable check |
|---|---|---|
| V1 | Service entry point | `<bin> serve --help` exits 0 (or a `<name>d` binary exists) |
| V2 | Local by default | the default bind is a Unix socket or `127.0.0.1` (`<bin> doctor` or `envinfo` shows it) |
| V3 | Surface parity | library, CLI and control plane list the same operation set (as W2) |
| V4 | Receipts are a contract | a receipt schema exists under `schemas/`, separating admitted, accepted and observed |
| V5 | No vendor credentials at rest | the secret scan passes; config schemas carry no credential fields with defaults |

MUST NOT: run the agent or harness it fronts, or decide for it; re-implement a primitive that a prim provides.

## 8. pressers: qualification harnesses (adjacent)

Stress, scale, fault and conformance-at-load testing for a **subject** (a contract or family of systems) lives in an
independent `<subject>presser` repo. It names the subject, not one backend, and carries many selectable suites. A prim's
`conformance/` proves correctness with small vectors. A presser proves behaviour at scale and under faults.

| # | MUST | Observable check |
|---|---|---|
| R1 | Deterministic packs | two runs with the same `--seed` produce the same pack digest |
| R2 | Independent oracle | the oracle package's dependency graph does not include the system under test |
| R3 | Offline evidence | `<bin> verify <pack>` succeeds with the network disabled |

SHOULD: report profiles, not a universal winner score.

## 9. When the check runs

At two moments only: **minting a repo** (C1 to C6 plus the class table) and **before a release** (all, including C7).
SHOULD items are never checked. There is no score and no certificate.

While this standard is `draft` and the repo-declaration schema and taxonomy file have not shipped, the check is a
**manual review step** at those two moments: a reviewer records the result in the mint brief or release checklist, and
a failing MUST is a finding to resolve or a declared extension to record, not an executable block. Once the schema,
the taxonomy file and a checker land, a failing MUST blocks that moment. That flip is recorded in this document's
status and version. Future tooling (`goneat assess --categories repo-class` or `crucible lint`) is out of scope.

## 10. New repo spec template

Fill this in, in the new repo's README or its first brief, before code:

1. **Name and class.** The suffix and the one-sentence primary-caller statement (§1).
2. **The job.** One sentence. What it never does (the class MUST NOT list, made concrete).
3. **Fulmen base and extensions.** Category, forge template (if any), each declared extension with its reason.
4. **Surfaces and operations.** The operation list and which surfaces expose it (parity, W2/V3).
5. **Contract.** Schemas it implements or emits, with crucible pins; for prims, profile A or B and the binding roadmap.
6. **Identity.** `env_prefix` (and any umbrella prefix), config path, `VERSION` start.
7. **Release.** Platforms, distribution channels, signing.
8. **Neighbours.** Prims it consumes, voys it calls, the presser that qualifies it.
9. **`.fulmen/repo.yaml`.** The filled-in declaration.

## 11. Changing class

A class change needs a decision record. Typical moves: extract a prim when a second program needs a bolt's or wit's
logic; promote a wit to a voy when others start queueing on it; split a wit that grows a second job.
