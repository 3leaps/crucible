---
id: "ADR-0018"
title: "Prims carry a multi-language commitment and may depend on sibling prims"
status: "proposed"
date: "2026-10-25"
deciders:
  - "@3leapsdave"
  - "cxotech"
  - "entarch"
scope: "Crucible foundation / repository classes"
tags: ["repository", "prims", "bindings", "conformance", "dependencies"]
---

# ADR-0018: Prims Carry a Multi-Language Commitment and May Depend on Sibling Prims

## Status

Proposed. Companion to the repository-classes standard
(`docs/standards/repository-classes.md`), which carries the observable checks.

## Context

The estate's primitive libraries share one suffix and one promise: another
program calls them in-process. Until now each repo decided its own language
story. Some ship a Rust core with a C ABI and cgo for Go; some ship Rust only
with bindings promised; one planned a pure-Go core. Consumers could not tell
from the name what they would get, and Go consumers that cannot carry cgo had
no path at all.

A second question arrived with the first dual-implementation prim: may a prim
depend on another prim, and what does that do to a pure-Go tree if the sibling
is Rust-core-only?

## Decision

1. **Every prim is consumable from Rust, Go, TypeScript and Python.** A binding
   not yet shipped is on the roadmap with its package name reserved. A CLI, if
   present, is a thin diagnostic surface over the same library and never a
   second implementation.
2. **Two profiles.** Profile A is one Rust core; Go uses cgo over the prim's
   JSON C ABI, TypeScript uses napi-rs, Python uses PyO3 and maturin, and no
   binding re-implements logic. Profile B is locked parallel implementations in
   pure Go and Rust, in one repo, under one contract, one version and one tag,
   passing one shared conformance suite; TypeScript and Python come from the
   Rust tree. Profile A is the default. Profile B is chosen when pure Go is a
   requirement.
3. **Prims may depend on sibling prims** under three rules: the sibling is
   pinned at a tagged release and is public before the dependent's own first
   public release; no sibling type appears in the dependent's public API,
   contract or conformance vectors; and a Profile B pure-Go tree depends only
   on cgo-free Go modules, so a Profile A sibling serves the Rust tree only.
   When the Go tree needs the same capability, the sibling grows a pure-Go tree
   or the dependent declares the gap. The dependent does not reimplement the
   sibling's logic to close it.

## Consequences

- A consumer can read a prim's profile and know whether cgo is required.
- Profile B doubles implementation cost. The shared conformance suite, run
  under both `go test` and `cargo test` with byte-identical normalised output,
  is what makes the two trees one product rather than two.
- A Profile A prim that a Profile B prim's Go tree needs becomes a candidate
  for its own pure-Go tree. That decision belongs to the sibling's owners and
  is made when a Go consumer needs it, not speculatively.
- Reimplementing a sibling's primitive in Go to avoid the dependency is ruled
  out. It recreates the duplication the family exists to retire.
- The machine-readable taxonomy and the repo-declaration schema named by the
  standard follow in a separate change.
