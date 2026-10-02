---
id: "DDR-0003"
title: "Portable path serialization at tool boundaries"
status: "proposed"
date: "2026-10-02"
last_updated: "2026-10-02"
deciders:
  - "@3leapsdave"
  - "entarch"
scope: "Crucible cross-platform tooling interfaces"
tags: ["portability", "paths", "validation", "interfaces"]
relates-to:
  - "crucible DDR-0002 (segmented snapshot identity and evidence)"
---

# DDR-0003: Portable Path Serialization at Tool Boundaries

## Status

**Proposed.** Pending maintainer ratification.

## Context

Filesystem paths, serialized tool arguments and JSON-pointer fragments have
distinct representation rules. Cross-platform tooling needs an explicit path
serialization contract without broadening the identities a validation report
may assert.

## Decision

- Supported cross-platform tooling and serialization boundaries where the tool
  reports or expects paths MUST use forward-slash file-path strings consistently
  in arguments and expected report
  identities, using Python `Path.as_posix()` or an equivalent adapter. Native
  filesystem `Path` values remain appropriate internally.
- URI and JSON-pointer fragments MUST remain separate typed or literal values.
  They MUST NOT pass through filesystem-path normalization.
- Validation reports MUST bind one-to-one to the complete submitted path
  strings. Duplicate, foreign, missing or extra identities MUST be refused as
  setup failures, not counted as successful validation or negative evidence.
  Basename matching and automatic case folding, alias expansion or realpath
  resolution MUST NOT widen this binding.
- Absolute versus relative paths MUST be selected explicitly for working-directory
  and temporary-file semantics. This decision does not mandate relative paths or
  moving temporary material into a repository.
- Native-only APIs requiring another syntax MUST use an explicit documented
  boundary adapter. Implementations MUST NOT blindly replace backslashes in
  arbitrary user data, URIs or identifiers.

## Consequences

Boundary adapters make the tool-facing representation explicit while keeping
filesystem operations and pointer syntax independent. Report identity remains
a strict interface check rather than an implicit filesystem lookup.

Boundary changes require detecting Windows and POSIX path-flavor regressions,
pointer-separation tests, duplicate/foreign/missing/extra report rejection and
full native evidence on supported platforms. Schema-id, validation-result,
diagnostic and process-exit checks remain fail closed. Path-flavor simulations
do not substitute for native execution.
