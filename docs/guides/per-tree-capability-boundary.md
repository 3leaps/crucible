# Adopter Guide: Observable Per-Tree Capability Boundaries

**Status:** Non-normative adopter guide.

This guide describes one accepted way to satisfy rule 3 of section 4.1 of the
[repository classes standard](../standards/repository-classes.md) for a
Profile B library whose Rust and Go trees do not offer the same capabilities.
Section 4.2 applies the same rule to shipped bindings, for the capability set
each binding declares. It changes no rule and adds no schema.

Out of scope: bindings that are declared optional and not shipped, and
command-line or terminal interfaces that exist only on the canonical host
tree. Those are outside library parity under section 4.2.

## Why This Matters

Rule 3 allows a per-tree capability gap when it is declared in `extensions`
with `scope: rust-only` or `scope: go-only`, and requires that the gap be
tested as an explicit `unsupported` refusal on the tree that lacks it.

Declaring the gap does not meet the second half. The refusal has to come from
the library, through a public call, and be graded by a shared vector on both
trees. None of the following is enough by itself:

- a list of capabilities with no call that refuses;
- a missing function or symbol;
- a typed error that does not identify the outcome as unsupported;
- an answer supplied by the test harness.

## First: Does the Governing Contract Define the Result

For each operation and condition, check whether the contract the library
implements already defines the result. Who owns the contract does not decide
this. A contract owned elsewhere, with a closed refusal list, may still
define a refusal for an unsupported capability or mode.

| Case | Answer for a missing capability |
| ---- | ------------------------------- |
| The governing contract defines a refusal for this operation and condition | That refusal, with the contract's spelling and precedence |
| The capability is an allowed optional feature and the contract's vocabulary has no result for its absence | A capability query owned by the repository, whose refusal explicitly says unsupported (recipe 1) |
| The operation is mandatory in the contract | Not a declarable gap. A tree without it fails qualification |

In the second case, do not reuse a contract category that looks close. A
contract refusal usually says something about an input, a value or a policy.
A missing optional feature says something about the build the caller linked.
A consumer that switches on category would otherwise treat a missing feature
as a data problem.

## Requirements

1. **A public refusal on every tree.** Each tree has a public call that, for a
   known capability it lacks, returns an explicit unsupported refusal.
2. **A shared vector grades it.** The same cases run on both trees. Where the
   contract has its own spelling for the refusal, the vector maps to that
   spelling.
3. **Declared gaps match the asymmetric set.** The `rust-only` and `go-only`
   entries in `.fulmen/repo.yaml` are checked by a test against the
   capabilities that differ between trees. Capabilities both trees share need
   no scope entry.
4. **Supported cases run the real operation.** A case that says a tree
   supports a capability calls that operation through the public API and
   checks its result. Checking a report alone proves nothing.
5. **Capability cases stay out of other owners' material.** They are never
   added to a vendored corpus or to another owner's contract vectors.
6. **A capability query does not replace contract cases.** Where the contract
   defines a refusal at dispatch, those negative cases are still executed. A
   condition that arises at run time is not a build gap and is not reported
   as one.

## Recipe 1: Optional Feature Outside the Contract's Vocabulary

Each tree exposes the same two calls:

- `capabilities` returns the identifiers this surface implements.
- `require(id)` returns success for an identifier this surface implements,
  and otherwise a capability error carrying the identifier and a disposition.

The capability error is its own type. It is not the contract's refusal type
and carries no contract category or rule. Its `unsupported` disposition is
the explicit refusal that rule 3 asks for.

The cases live in a suite the repository owns, for example
`conformance/capabilities/v0/`, shared by both trees and run on both. A case
has three fields: the surface, the capability and the expected disposition.

Choices this recipe makes that the standard does not require:

- **A static registry.** Both calls read one list fixed at build time, with no
  options, negotiation or version ranges. It keeps the test from passing on a
  value the test supplied.
- **A distinct `unknown` disposition.** An identifier that names no capability
  gets `unknown` rather than `unsupported`, because the fixes differ.
- **Per-surface reports.** Where a tree is split into several packages or
  crates, each surface reports only what it implements, and an application
  that links several composes their reports. The suite names each surface and
  compares its report exactly.

## Recipe 2: The Contract Defines the Refusal

Use the contract's refusal, at its position in the contract's refusal
precedence. Express the negative cases as a separately identified group in
the conformance set, not mixed into the cases that judge the operation's
results. A negative case tests dispatch only; it is not evidence that the
operation is qualified.

Once a second tree or a per-language difference exists, requirements 1 to 3
apply: the refusal is reachable from the library surface on each tree, the
same cases run on both, and the scope entries match the capabilities that
differ. A library with a single tree has no gap to declare.

## What This Guide Does Not Do

- It does not make a capability gap acceptable by itself. Rule 3 still
  limits when a gap may be declared.
- It does not exempt shared behaviour. Everything outside the declared
  capabilities stays under the shared conformance suite for both trees.
- It adds no duties to the standard's checks. The recipe choices above are
  options.
- It is not a negotiation protocol between processes.
