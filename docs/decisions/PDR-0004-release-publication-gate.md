---
id: "PDR-0004"
title: "The signed tag authorizes publication; CI verifies and publishes"
status: "accepted"
date: "2026-07-17"
last_updated: "2026-07-20"
deciders:
  - "@3leapsdave"
  - "cxotech"
scope: "Crucible foundation / release process"
tags:
  - "process"
  - "release"
  - "ci"
  - "governance"
relates-to:
  - "crucible RELEASE_CHECKLIST.md (the checklist this PDR corrects)"
  - "crucible .github/workflows/release.yml (the workflow this PDR changes)"
  - "crucible ADR-0003 (the *DR taxonomy; PDR = a revisable ways-of-working choice)"
---

# PDR-0004: The Signed Tag Authorizes Publication

## Status

**Accepted.** Corrects a release-process defect that has recurred on consecutive
releases. Implemented in the same change that files this record.

## Context

Crucible publishes releases as signed git tags. `release.yml` triggers on tag
push, verifies the tag/VERSION match, runs quality gates, and creates a GitHub
Release with `draft: true`. The workflow comment states the intended posture:

> `Posture: draft -> sign -> undraft (signing/publish is separate process)`

A maintainer is then expected to undraft the release manually.

**The posture describes a sequence that cannot occur.** Signing is what _creates_
the tag object; a tag is signed before it is pushed, and the push is what
triggers the workflow. So by the time `release.yml` runs, the tag is **already
signed**. There is no window in which a draft release awaits a signature — the
draft gate guards a condition that cannot exist.

**Observed failure.** The manual undraft has now been missed on two consecutive
releases:

| Release | Tagged     | Published  | Dark for |
| ------- | ---------- | ---------- | -------- |
| v0.1.18 | 2026-07-06 | 2026-07-06 | hours    |
| v0.1.19 | 2026-07-09 | 2026-07-17 | 8 days   |

In both cases the tag was correctly signed, verified by GitHub, and every gate
passed. Only the final manual click was missing. For eight days, a released
contract alignment was invisible to every downstream consumer, and the prior
release still carried the `Latest` flag — so a consumer checking "what is the
current standard?" got a stale, confidently-wrong answer.

**Why documentation is not the control here.** The natural reflex is "add the
step to the checklist." That reflex is wrong twice over:

1. **The checklist does not omit the step by accident — it certifies the wrong
   condition.** `RELEASE_CHECKLIST.md` contains zero occurrences of "draft" or
   "publish". Its Post-Release section asks the maintainer to verify that the
   workflow "creates GitHub Release" and to "spot-check release notes render
   correctly." **Both tick green while the release is still a draft.** The
   checklist reaches a false-complete state. It does not merely fail to remind;
   it actively signals done.

2. **Even a correct checklist item would be a weak control.** A manual step whose
   omission produces no signal — no failed build, no red badge, no alert; the
   repo looks perfect and the tag verifies — is a step that will be missed again.
   The only feedback channel is a human noticing an absence, which is the
   weakest detection mechanism available.

The standing tension: **a human gate before public exposure** versus **a release
process with no silent-failure mode.**

## Decision

**The signed tag is the publication authorization. CI verifies the signature and
publishes. The manual undraft step is eliminated.**

1. **Signing is the authorization act.** Pushing a GPG-signed, maintainer-created
   tag is a deliberate, authenticated, non-accidental act that already expresses
   intent to release. The undraft click adds **no authority the signature did not
   already carry** — only latency and a silent-failure mode. The release body is
   `body_path`-sourced from `docs/releases/vX.Y.Z.md`, which was already reviewed
   and merged through a PR. Nothing is reviewed at undraft time that was not
   reviewed earlier.

2. **CI verifies the signature against the pinned release key before
   publishing.** Once the signature carries publication authority, _whose_
   signature matters more than _whether GitHub recognizes one_:
   `verification.verified == true` holds for a signature by **any** GPG key
   uploaded to the tagger's account, so on its own it reduces the publication
   gate to "anyone with tag-push rights and a self-uploaded key" — a compromised
   account mints publishable releases. Two assertions, both required:
   - **Key identity (authoritative):** the tag verifies in an isolated keyring
     built solely from the release keys committed at
     `docs/security/release-signing-keys.asc`, with a full-fingerprint
     `VALIDSIG` match. The pin file is reviewed like any other change; rotating
     the release key requires a PR that updates it (see Consequences).
   - **Account linkage (secondary):** GitHub reports the tag verified — the
     checklist **already documents this exact call**, labelled "CI-friendly";
     it was written for this purpose and never wired in:

   ```bash
   TAG_SHA=$(gh api repos/3leaps/crucible/git/ref/tags/vX.Y.Z --jq .object.sha)
   gh api repos/3leaps/crucible/git/tags/$TAG_SHA --jq .verification
   ```

   The verified authorization is the **annotated tag object**, not merely the
   mutable ref name. CI records that object's SHA, uses the same SHA for both
   signature assertions, carries it across the job boundary, and immediately
   before publication requires `refs/tags/vX.Y.Z` to still resolve to that exact
   object. A lightweight tag, a missing object identity, or a changed ref fails
   closed.

3. **Publish non-draft; set `Latest` explicitly.** A verified stable tag publishes
   with `draft: false` and is marked `Latest`. `Latest` is set explicitly rather
   than assumed — a previous release does not yield the flag on its own, which is
   the second half of what went wrong on v0.1.19.

4. **Prereleases publish as prereleases, not as drafts.** The existing
   alpha/beta/rc detection sets `prerelease: true` and does **not** take `Latest`.
   A prerelease is a published artifact with reduced status, not a hidden one.

5. **Draft becomes the failure mode, not the happy path.** If signature
   verification fails, the job **fails loudly** and the release is left unpublished.
   This inverts the current semantics: today a draft means "normal, awaiting a
   human"; under this PDR a draft means "something went wrong, look at it." An
   unpublished release becomes a red signal instead of an ambiguous one.

6. **Correct the checklist to match.** Post-Release verifies **published** state —
   release is non-draft, carries `Latest`, and is reachable — not merely that a
   Release object was created. The checklist stops being able to reach
   false-complete.

7. **Precondition: version-tag refs are protected.** Publication authority now
   flows through `refs/tags/v*`, but branch protection guards `main` only. A
   ruleset restricting who may create or update version tags is a precondition
   of this posture — without it, the write-access boundary and the publish
   boundary silently merge. (The pinned-key assertion in §2 bounds the damage —
   an unauthorized tag cannot publish — but tag-ref protection keeps the
   unauthorized tag itself from existing.) The repository's active version-tag
   ruleset, named `Tag Publish Protection`, covers only `refs/tags/v*`, blocks
   creation, update, deletion, and non-fast-forward changes, and grants its sole
   always-on bypass to organization administrators.
   The policy crosses the publication boundary in three explicit assertions:
   - **Full pre-tag assertion.** `make release-tag` runs the complete ruleset
     guard with the maintainer's release-administration credential, including
     the exact bypass-actor list.
   - **Signed handoff.** The guard canonicalizes the expected policy and embeds
     its SHA-256 fingerprint in the annotated tag message. The tag signature
     therefore covers both the release intent and the full-policy assertion.
   - **Read-only publication assertion.** CI checks every ruleset field visible
     to its standard read-only `GITHUB_TOKEN`, then requires the signed tag to
     carry the exact full-policy fingerprint before publishing.

   This split is necessary because GitHub deliberately omits `bypass_actors`
   unless the API caller can write the ruleset. Giving release CI a ruleset-write
   credential merely to reveal that field would enlarge both the secret boundary
   and the mutation boundary. The CI assertion must be honest about what it can
   observe; the signed tag carries the complete assertion it cannot repeat. The
   bypass boundary and release-key custody boundary remain organization-level
   controls.

8. **Publication dependencies are immutable.** Every third-party action in the
   check and release workflows is referenced by a full commit SHA, with the
   reviewed semantic version retained as a comment. A movable upstream action
   tag cannot change the code that receives release write permission.

## Rationale

- **Removing a step beats remembering a step.** The failure was a missing manual
  action; the durable fix is to not require the action. A control that depends on
  recall has already been measured at 0-for-2.
- **The gate was guarding an impossible condition.** Once you see that the tag is
  signed _before_ the workflow runs, the draft posture has no threat model left to
  defend. It is not a weakened safeguard — it is a safeguard against nothing.
- **Silent failures are the expensive kind.** Every other release defect surfaces
  as a red check. This one surfaced as a repo that looked perfect. Converting it
  into a build failure puts it in the same feedback channel as everything else.
- **The mechanism already exists in-repo.** The signature-verification call is
  written down, marked CI-friendly, and unused. This PDR mostly connects two
  things crucible already has.

## Consequences

**Positive**

- No release can be signed, tagged, green, and invisible.
- `Latest` is always accurate — downstream consumers asking "what is current?" get
  a correct answer without a human having remembered anything.
- Publication latency drops from "whenever the maintainer returns" to CI duration.
- The checklist can no longer certify a false-complete state.
- Signature verification and publication remain bound to one annotated tag
  object even if the ref is changed between jobs.
- The tag-protection precondition is executable rather than documentary.
- A successful full-policy assertion is carried through publication as a signed
  policy fingerprint without giving CI ruleset-write authority.

**Negative / costs (accepted)**

- **The staging window is genuinely lost.** A maintainer who pushes a signed tag
  and then wants to reconsider before public exposure no longer has a private
  buffer. This is accepted deliberately: pushing a signed tag is already the point
  of no return for the _tag_, which is the un-editable public artifact; the
  release object is the lesser exposure. A change of mind after tag push is a
  rollback, and the checklist already documents that path. **Staging, when
  genuinely wanted, is the prerelease channel:** an rc tag publishes as
  `prerelease: true` without `Latest` (§4). That is the sanctioned buffer — do
  not re-introduce drafts to get one.
- **Key rotation gains a step.** The pinned key file
  (`docs/security/release-signing-keys.asc`) must be updated — by reviewed PR,
  before the first tag signed by the new key — whenever the release key rotates.
  A forgotten pin update fails closed (the release stays unpublished and the job
  is red), which is the correct direction, but rotation choreography must
  include the pin or the first post-rotation release will block.
- **Key _expiry_ is the same failure, and it arrives unprompted.** Rotation is
  chosen; expiry is not. When the pinned signing key or subkey passes its
  expiration date, verification yields an expired-signature result rather than a
  valid one, and releases stop publishing until the pin is refreshed — with no
  preceding action by anyone to prompt it. Adopting this posture therefore means
  tracking the expiration dates of the pinned material as a release-path
  dependency, not merely as a security-hygiene item. Refresh the pin ahead of
  expiry; the fail-closed direction is correct, but an unplanned block is
  avoidable.
- If `Latest` should ever _not_ follow the newest stable tag, that now requires an
  explicit override rather than being the accidental default.
- CI gains a dependency on GitHub's verification API. If it is unavailable the job
  fails closed (unpublished) — the safe direction, and the same state as today.
- Local release tagging gains a dependency on the GitHub rulesets API and a
  maintainer credential capable of viewing bypass actors. Missing access or an
  unavailable API blocks tagging until the complete policy can be verified.
- Tags created outside the release script do not carry the policy fingerprint
  and fail publication even if their cryptographic signature is otherwise valid.

## Alternatives considered

- **Add the missing step to the checklist.** Rejected as the primary fix. It
  corrects the false-complete bug (which this PDR does anyway, in §6) but leaves a
  recall-dependent control whose omission still produces no signal. It treats the
  symptom that was measured to fail.
- **Keep the draft; alert when a release stays drafted.** Rejected. It adds a
  second mechanism to compensate for the first mechanism's redundancy — more
  moving parts to defend a gate that guards nothing.
- **Keep the draft; block the next release while a prior one is drafted.**
  Rejected for the same reason, and it detects the problem exactly one release
  too late.
- **Give CI a ruleset-write credential.** Rejected. GitHub would reveal bypass
  actors, but a publication job would gain authority to mutate the control it is
  supposed to attest. The signed-handoff design preserves a read-only CI token.

## References

- [RELEASE_CHECKLIST.md](../../RELEASE_CHECKLIST.md) — the checklist corrected by §6
- [GitHub REST API: Get a repository ruleset](https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset) — documents bypass-actor visibility for callers with ruleset write access
- [ADR-0003: Decision & Governance Record Taxonomy](ADR-0003-decision-record-taxonomy.md) — defines PDR
- [PDR-0002: Worktree per task](PDR-0002-worktree-per-task.md) — sibling process record

## Revision History

| Date       | Status Change | Summary                                                  | Updated By |
| ---------- | ------------- | -------------------------------------------------------- | ---------- |
| 2026-07-17 | → proposed    | Signed tag authorizes publication; CI verifies+publishes | cxotech    |
| 2026-07-19 | → accepted    | Filed with its implementation; draft posture removed     | cxotech    |
| 2026-07-20 | accepted      | Bind exact tag object; enforce ruleset and action pins   | secrev     |
| 2026-07-20 | accepted      | Carry full policy in tag; use honest read-only CI view   | secrev     |
