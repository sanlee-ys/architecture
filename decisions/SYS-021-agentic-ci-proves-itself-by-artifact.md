# SYS-021: An agentic CI job proves itself by its artifact, never by its exit code

**Status:** Accepted
**Date:** 2026-07-24
**Deciders:** San Lee

---

## Context

Every CI lane in this system until now has been **deterministic**: `pytest`, `ruff`, `mypy`,
the contract-schema check (`SYS-018`), the metrics-artifact checks (`SYS-019`), the eval gates
(`SYS-017`). They share a property nobody had to state, because it has never been violated —
**a deterministic job that does nothing fails loudly.** A test suite that cannot import its
module errors. A linter with no files errors or reports zero explicitly. The exit code and the
work are the same event.

On 2026-07-24, `defense-news-classifier` gained its first **agentic** CI lane
(`claude-code-action` posting PR reviews, its `ADR-016`). That lane broke the property three
times in one sitting, and only the first break was visible:

| # | Cause | What CI showed |
|---|---|---|
| 1 | Missing `id-token: write` (OIDC scope) | **Red.** Caught in minutes. |
| 2 | Missing `--allowedTools` | **Green, 36s, $0.14 spent, 7 turns, zero comments posted.** |
| 3 | PR edited the lane's own workflow file | **Green, job never executed at all.** |

Break 2 is the instructive one. Claude read the diff, formed a review, attempted to post it six
times, was refused each time, and exited 0 — `permission_denials_count: 6`. **A tool denial is
not a job failure.** Break 3 is the action's own guard refusing to run a workflow whose head-ref
content differs from the default branch's; also not a failure.

The common shape: the deliverable of an agentic job is a **side effect** (a posted comment, a
written file, an opened issue), while the exit code reports only whether the *harness* ran.
Those are different events, and the gap between them is silent. Two of three breaks were
indistinguishable from success on the checks list, and would have been discovered only by
someone eventually noticing that no PR ever gets commented on.

This is `SYS-019`'s finding — *the surface that looks like proof is not proof* — arriving in a
new place. `SYS-019` governs **documented claims**; this governs **job execution**. The tension
between them is real and is addressed in the Decision.

## Decision

**Any agentic CI lane must name its deliverable, be granted the tools to produce it, and be
verified by that deliverable's existence at adoption. A green pipeline is never accepted as
evidence that an agentic lane works.**

Four requirements, each traceable to a break above:

1. **Grant tools explicitly.** The default grant is effectively read-only; the agent can think
   and cannot act. Name the write tools (`--allowedTools` or the harness equivalent) and state
   in the prompt that producing the artifact *is* the task. *(Break 2.)*
2. **Verify at adoption with a live end-to-end run, and record it.** Not a dry run, not a green
   check — an actual artifact produced by the real trigger, on the real repo. The adopting PR or
   ADR records what was observed. *(Breaks 2 and 3.)*
3. **Enforce advisory status mechanically.** A lane that is *meant* to be non-blocking must
   carry `continue-on-error: true` (or equivalent). Intent recorded in prose is not enforcement;
   an infrastructure failure otherwise reddens a PR whose real gates are green, which teaches
   exactly the habit — red is negotiable — that the deterministic gates depend on not existing.
4. **Guard the trigger surface, because the platform's defaults are asymmetric.** On GitHub,
   `pull_request` from a fork **fails closed** (secrets withheld). `issue_comment` **fails open**
   — it runs in the base repo's context *with* secrets regardless of who commented, so on a
   public repo an unguarded `@agent` phrase is an open spend vector on the repo owner's API key.
   Gate it (`author_association`) at the workflow level, ahead of the harness. Related:
   `SYS-016`.

**On the tension with `SYS-019`.** That decision says a claim with a machine-readable source of
truth must be asserted mechanically, and a human-read list is the weakest instrument. Applied
here, the strongest instrument is genuinely weaker: an advisory review's *absence* is not an
error condition — there is no artifact whose staleness a build can compare against, because "no
findings worth posting" and "muted by a permission denial" produce the same empty result. So
this decision does not claim `SYS-019`-grade enforcement. It requires **verification at
adoption** — the one moment when the difference between "working" and "silently muted" is
cheaply observable — and it says plainly that continuous assurance is not provided. Naming that
bound is the point; `SYS-019`'s failure mode was a check believed to cover more than it did.

## Downstream surfaces

- **`defense-news-classifier/decisions/016-claude-code-action-pr-review.md`** — the first
  instance and the source of all three breaks. It already records them repo-locally; this
  decision generalises them. No edit needed.
- **`defense-news-classifier/.github/workflows/claude-review.yml`** — compliant as of
  2026-07-24 (tools granted, `continue-on-error`, `author_association` guard, verified live).
- **`kb-agent`** — second instance, adopted alongside this decision. Same four requirements.
- **`engineering/README.md`** — the house CI conventions live there. This decision is the rule
  those conventions instantiate for agentic lanes specifically; a pointer belongs there when
  that file is next revised. **Not edited here** — deliberately, so this decision is not itself
  an unverified claim about a surface it did not touch.
- **`SYS-017` (evals-as-CI)** — unaffected. Its gates are deterministic and keep the
  fails-loudly property; this decision exists precisely because agentic lanes do not.
- **`SYS-019`** — complementary, not superseded. See the tension note above.
- **`SYS-016` (agent–tool seam threat model)** — requirement 4 is a concrete instance of that
  threat model at the CI trigger surface.
- **Any future agentic lane** (auto-triage, doc generation, scheduled agents) — gated by this
  decision rather than re-derived per repo.

## Consequences

- **What this makes easier:** adopting an agentic lane in a second, third, or fourth repo
  without rediscovering the same three failures. The requirements are a checklist with a
  known provenance, not folklore.
- **What it costs:** a manual verification step at adoption that cannot be automated away, and
  the honesty tax of admitting the lane is unverified between adoptions. Also a small ongoing
  cost: agentic lanes need their tool grants revisited when the harness's defaults change.
- **What it forecloses:** treating "the workflow is green" as adoption evidence. Under this
  decision an agentic lane is not considered working until an artifact has been observed.
- **A known, accepted hole:** requirement 2 verifies at adoption; nothing detects a lane that
  goes silently mute *later* (an expired key, a changed default, a revoked scope). Two of the
  three breaks would recur invisibly. Accepted for now because the failure is
  degraded-advice, not wrong-advice, and the lane is advisory by construction.
- **Revisit when:** a third agentic lane lands, or when one is ever promoted from advisory to
  gating. Gating changes the risk calculus entirely — a silently-muted *gate* is a hole in the
  build, not a missing opinion — and this decision does not authorise that promotion.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **Leave it in `defense-news-classifier`'s ADR-016** | The three breaks are properties of agentic CI, not of that repo. Leaving it there means the second repo rediscovers them at the same cost, which is the drift `SYS-001` created this log to prevent. The trigger for promoting it was literally adopting the lane in `kb-agent`. |
| **Require a mechanical check that the artifact exists (full `SYS-019` treatment)** | Attractive and dishonest. "No comment posted" is ambiguous between *muted* and *nothing worth saying*, so any such check either fails on clean PRs or passes on muted ones. Asserting a guarantee the mechanism cannot deliver is worse than naming the bound — that is `SYS-019`'s own lesson about checks believed to cover more than they do. |
| **Ban agentic CI lanes; keep CI deterministic** | Overcorrects from three fixable configuration errors. The lane demonstrably produced a substantive, repo-specific review once configured. The property worth protecting is that *deterministic gates stay deterministic*, which requirement 3 secures directly. |
| **Make the review lane a gate so muteness would be conspicuous** | Inverts the risk: a non-deterministic reviewer with merge authority turns every model error into a blocked merge, and trains the habit of merging past red. It also would not have caught break 2 — a muted run exits 0, so it would have gated on nothing while appearing to gate. |
| **Rely on noticing that no comments ever appear** | This is what "unverified" means, stated as a plan. It is exactly how break 2 would have been found: eventually, by accident, after an unknown number of PRs went unreviewed while appearing reviewed. |
