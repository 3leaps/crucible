---
title: "Composing a Review Panel"
description: "The composition companion to the fierce-collaboration review standard: how a seat is assembled from identity, environment, harness, mode, and framing — before the run-book's Step 0 can begin"
author: "Claude Fable 5"
author_of_record: "Dave Thompson <dave.thompson@3leaps.net>"
supervised_by: "@3leapsdave"
date: "2026-07-31"
last_updated: "2026-07-31"
status: "draft"
category: "guide"
tags: ["review", "fierce-collaboration", "panels", "agents", "composition", "how-to"]
---

# Composing a Review Panel

The [fierce-collaboration review standard](../standards/fierce-collaboration-review.md)
defines what must hold in a relied-upon review, and the
[run-book](running-a-fierce-collaboration-review.md) walks the review itself
from declaration to close-out. Both assume the seats already exist. This guide
covers what comes **before** — how each seat is composed and launched, and how
a whole panel is assembled so its diversity is designed rather than accidental.
The standard is normative; where this guide and the standard disagree, the
standard wins.

The one-sentence version: **a seat is not a prompt.** The same prompt, run
under a different profile, working directory, or identity, is a different seat
— and every launch failure we have observed across multi-reasoner panels lived
in a layer of the composition that was implicit instead of declared.

**If you cannot compose and launch a panel from this page, that is a defect in
this page.** File it.

## The five-layer composition model

A seat launch is a composition of five layers:

```
(identity) × (environment) × (harness + profile) × (mode) × (framing + capture)
```

| Layer                 | What it is                                                                                                                                                                                                                                                                      | Failure when left implicit                                                                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Identity**          | Which seat this is — the role and scope the participant occupies, and the credentials that make it that seat and not another.                                                                                                                                                   | A seat runs as whoever launched it; its posts, commits, and tool access misattribute.                                                                                                                 |
| **Environment**       | The repository-scoped variables and credentials the seat's tools need. Non-interactive launches do not run interactive shell hooks, so environment that "is always there" in an operator's terminal is invisible to a headless seat unless the launcher composes it explicitly. | Tools report "not authenticated" mid-review despite valid operator credentials; the seat improvises or fails.                                                                                         |
| **Harness + profile** | The execution vehicle (see harness classes below) plus the operator-provisioned permission or sandbox profile it runs under, referenced **symbolically** by name.                                                                                                               | Permission prompts hang a headless run; sandbox denials push caches and writes into invented locations; flag vocabulary is cargo-culted across vehicles that assign the same flag different meanings. |
| **Mode**              | `interactive` (live multi-turn session) · `headless` (non-interactive single-turn or scripted run) · `subagent` (spawned inside an orchestrating session, sharing its working tree).                                                                                            | A disposition is compared across seats that did not run the same way, and the difference is silently attributed to reasoner or framing.                                                               |
| **Framing + capture** | The prompt skeleton (the six-part framing block below) and the declared path by which the seat's output enters the record.                                                                                                                                                      | The verdict lives only in a scrollback buffer; a truncated capture cuts mid-finding and the record understates what the seat found.                                                                   |

Reproducibility of a seat's verdict requires **all five layers recorded**, not
just the prompt. The machine-readable form of that record is the seat's
`execution` object in the
[`review-journal/v0`](../../schemas/review-journal/v0/) manifest — symbolic
`harness`, symbolic `profile_ref`, `mode`, and `capture` — required for every
compared seat whenever a framing-comparison claim is made from the journal
(standard §9.2).

**Symbolic references are the durable form.** Launch flags drift with tool
versions; filesystem paths and profile contents are operating detail that does
not belong on a public surface (standard §10). A record therefore names the
harness **class** and the profile **by name**, and the operator's launch matrix
— maintained outside the record — resolves the name to whatever the current
tooling actually requires. If you find yourself writing a raw invocation string
into a prompt, a journal, or an alignment log, stop: that is the drift-prone
and scrub-hostile form of a fact the symbolic reference states durably.

## Harness classes

Three classes cover the panels run to date. A record names the class (or a
symbolic product token the operator's matrix defines); it never embeds the
invocation.

### 1. Orchestrator-native subagent

A seat spawned **inside** an orchestrating session, sharing its working tree,
credentials, and tool plumbing. Capture is structural — the orchestrator
receives the seat's output directly as a tool result.

- Cheapest to compose: identity and environment are inherited, so layers 1–2
  come free.
- Not reachable from outside the orchestrating harness; these seats belong to
  the orchestrator and cannot be driven by external dispatch tooling.
- The inheritance that makes them cheap also makes them **correlated**: a
  subagent shares the orchestrator's reasoner family unless the harness offers
  an explicit override, and it shares the orchestrator's view of the tree.
  Check the panel-diversity rule below before staffing approving seats this
  way.

### 2. Unsandboxed headless CLI

A vendor CLI run non-interactively in the operator's own environment — no
sandbox profile, single-turn, prompt in, verdict out.

- Inherits the operator's shell credentials and filesystem access; layers 1–2
  are usually correct by inheritance, which is why this class tends to "just
  work" while sandboxed classes need composition.
- That same inheritance means the seat runs with the operator's full authority:
  fine for read-only review seats under the read-only rule below, not a
  substitute for a sandbox where one is warranted.

### 3. Sandboxed headless CLI

A vendor CLI run non-interactively under an operator-provisioned permission or
sandbox profile. This is the class where every layer must be explicit, and the
class that produces panel diversity across vendors. Its composition rules:

- **Profile by name.** The profile is provisioned by the operator ahead of
  time and referenced symbolically. Its contents — path allowlists, network
  rules — live with the operator, not in the record and not in the prompt.
- **Approval policy set for headless.** Sandboxed CLIs commonly route
  escalations to an interactive approval mechanism. A headless seat has no
  interactive channel, so the launcher must set the vehicle's
  never-ask/fail-closed policy explicitly — otherwise the seat hangs silently
  or dies mid-pass with no operator-visible prompt.
- **Working directory pinned and verified.** Every vendor CLI operates on the
  current directory, and multi-repository workspaces make wrong-directory the
  single most common launch failure. The launcher sets the directory
  explicitly and verifies it is the intended repository (check the remote,
  not just the path) before the seat runs.
- **Environment composed, not assumed.** Whatever credential or variable
  loading the operator's interactive shell performs, the launcher performs
  explicitly for the seat.

### Cross-class footguns

These recur, and each is a composition rule rather than a debugging exercise:

| Footgun                                  | Rule                                                                                                                                                                                                                                               |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Same flag, different meaning per vehicle | Never carry a flag from one vehicle to another on resemblance. The launch matrix records each vehicle's vocabulary; seats are launched from the matrix, not from memory.                                                                           |
| Wrong working directory                  | Pin and verify per launch. The prompt's "you are reviewing repository X" is discipline, not enforcement; the launcher's directory check is enforcement.                                                                                            |
| Credentials invisible off-terminal       | Compose environment in the launcher. If a tool works in your terminal and fails in the seat, suspect layer 2 before suspecting the tool.                                                                                                           |
| Interactive interceptors in the path     | Repository hooks or wrappers that raise interactive approvals hang headless seats silently. Pre-flight for them and remove or bypass them for the run.                                                                                             |
| Capture by terminal scrape               | A tail of the terminal is not a record: it loses structure and can cut mid-finding. Capture the seat's **last message to a file** or use the vehicle's **structured output**; the journal's capture enum deliberately has no terminal-scrape form. |

## Panel diversity mechanics

Composition is also a panel-level concern — the roster is composed, not just
the seats:

- **Smallest roster that covers the real risk surface** (standard §3). An
  unused seat is ceremony.
- **At least one approving seat off the implementer's reasoner family.** The
  correlated-priors rule (standard §3) is checked at composition time, when it
  is cheap, not discovered at Step 0, when it costs a relaunch. A reviewer
  that reasons like the implementer is most likely to miss what the
  implementer missed — and in the field, the finding that saved a two-line
  docs fix from reintroducing its own defect class came from the one seat on
  a different reasoner family.
- **Mode is part of independence.** An approving seat spawned as a subagent of
  the session that authored the change shares that session's context and
  correlates with it; the standard's rule that a seat does not review its own
  authored change in the same execution context (§3) reaches this case. Prefer
  headless or live seats for approvals of work the orchestrating session
  produced.
- **Disclose the composition tally at Step 0.** The run-book's
  correlated-priors check consumes what this guide produces: reasoner and
  execution disclosures per seat. A clean tally is withdrawable on the record;
  an unexamined one is a latent bound on the green.

## The six-part framing block

Every review seat's prompt carries the same skeleton. Framing is the primary
lever against reviewer variance (standard §11), and the block exists so the
lever is set deliberately, six named parts, none skipped:

1. **Role line** — "You are `<catalog-role>`, reviewing `<artifact>`" —
   matching the identity the seat actually runs under (layer 1: if the role
   line and the sourced identity disagree, the composition is wrong).
2. **Target** — the exact artifact: commit or content anchor, file paths, and
   how to materialize them (standard §9.1 anchor forms).
3. **Spec context** — what was _supposed_ to be true, in two to six sentences,
   with upstream references where they exist. The seat verifies against the
   spec, not against the diff's own story.
4. **Named review dimensions** — the specific traps for this change, through
   this seat's lens. "Review this" is not a framing.
5. **Non-negotiables** — the constraints that must not break, stated as
   constraints: compatibility-critical surfaces, the **read-only rule** (the
   seat modifies nothing), never editing generated or synchronized trees.
6. **Verdict contract** — the normative form is standard §9.3: one binary
   disposition token closing the output, mapped to the canonical vocabulary;
   numbered severity-tagged findings; a declared word cap. The framing block
   is where the token pair and the cap are declared.

A template appears at the end of this page.

### Implementation-seat variant

An implementation seat (a seat that writes code, in subagent or interactive
mode) uses the same skeleton with two substitutions:

- The **verdict contract** becomes a **return contract**: files changed, test
  results, judgment calls made, deviations from the brief with justification.
- The non-negotiables carry a **do-not-commit rule**: the seat stages nothing
  and commits nothing. The orchestrator reviews the work and owns every
  commit, so accountability stays in one place.

**Seats are read-only; the orchestrator commits.** This is the composition-side
face of author-≠-approver: every defect the field panels caught was caught
_because_ the reviewing seat had no stake in the diff. A review seat with write
access to the artifact under review is a composition defect, whatever its
prompt says.

## Preflight checklist

Run before dispatching any seat; every line is a launch failure someone paid
for once.

```markdown
- [ ] Identity resolves: the seat's role/scope credentials load, and the role
      line in the framing matches them.
- [ ] Environment composed: the seat's tools authenticate from a
      non-interactive launch (probe one credentialed call, don't assume).
- [ ] Profile exists: the symbolic profile_ref resolves in the operator's
      launch matrix, and the profile loads on the current tool version.
- [ ] Working directory pinned: set explicitly, verified against the intended
      repository's remote.
- [ ] Approval policy set: headless seats run under the vehicle's
      never-ask/fail-closed policy; nothing in the path raises an interactive
      prompt.
- [ ] No interactive interceptors: repository hooks and wrappers checked for
      approval popups before dispatch.
- [ ] Capture declared: last-message file path (writable) or structured
      output — decided before launch, not after.
- [ ] Framing complete: all six parts present; verdict contract (or return
      contract) declared with token pair and word cap.
- [ ] Role prompt pinned: {slug, version} resolved, digest computed where run
      comparability matters (standard §12).
- [ ] Execution record ready: harness, profile_ref, mode, capture known for
      this seat — the journal manifest will carry them (standard §9.2).
- [ ] Diversity checked: at least one approving seat off the implementer's
      reasoner family; subagent approvals of the orchestrator's own work
      avoided.
```

## Recording the composition

When the panel emits a journal, each seat's composition lands in the manifest
as its `execution` object:

```json
{
  "seat": "devrev",
  "participant": {
    "id": "p-devrev",
    "kind": "agent",
    "reasoner": { "name": "reasoner-family-b", "version": "b.2" }
  },
  "execution": {
    "harness": "harness-class-headless-cli",
    "profile_ref": "profile-review-seat",
    "mode": "headless",
    "capture": "last-message-file"
  },
  "role_prompt": { "slug": "devrev", "version": "1.1.1", "digest": "sha256:…" }
}
```

Optional in v0; required for every compared seat when a framing-comparison
claim is made from the journal (standard §9.2). Without a journal, the same
facts belong in each seat's execution disclosure in the alignment log —
symbolically, per the standard's §3 disclosure rule.

## Templates

### Review-seat framing block

```markdown
You are <catalog-role>, reviewing <artifact> at <anchor>.

Target: <how to materialize it — e.g. the commit to show, the paths to read>.
Context: <2–6 sentences: what this change is supposed to do, with upstream
references where they exist>.
Review for: <named dimensions — the specific traps for this change through
this seat's lens>.
Non-negotiables: <compat-critical constraints>. You are read-only: modify
nothing, stage nothing, commit nothing.
End with exactly one verdict token — <ACCEPT-FORM> or <CHANGES-FORM> — plus a
numbered, severity-tagged (P1/P2/P3) findings list. Maximum <N> words.
```

### Implementation-seat framing block

```markdown
You are <catalog-role>, implementing <brief> in <repository> at <anchor>.

Target: <the branch/paths to change>.
Context: <2–6 sentences of spec>.
Constraints: <named non-negotiables>. Do not commit: the orchestrator reviews
and owns all commits. Never edit generated or synchronized trees.
Return: files changed, test results (run them), judgment calls made, and any
deviation from this brief with its justification.
```

### Execution disclosure (alignment-log form)

```markdown
Seat: <seat> · harness: <class-or-token> · profile: <symbolic-ref | none> ·
mode: <interactive | headless | subagent> · capture: <form> · reasoner:
<name+version | "not exposed by this harness"> · role prompt: <slug>@<version>
```

## Relationship to the other records

| Question                            | Where it lives                                                          |
| ----------------------------------- | ----------------------------------------------------------------------- |
| What must hold in the review        | The [standard](../standards/fierce-collaboration-review.md) (normative) |
| How to run the review, step by step | The [run-book](running-a-fierce-collaboration-review.md)                |
| How to compose and launch the seats | This guide                                                              |
| The machine-readable record of both | [`schemas/review-journal/v0`](../../schemas/review-journal/v0/)         |

Launch matrices, profile contents, and per-vehicle invocation detail are
operator-side material, maintained wherever the operator keeps operating
detail — deliberately not here.
