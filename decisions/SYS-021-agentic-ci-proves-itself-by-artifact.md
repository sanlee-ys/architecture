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
3. **Enforce advisory status mechanically — at the _step_, not the job.** A lane that is *meant*
   to be non-blocking must carry `continue-on-error: true` **on the step that can fail**. Intent
   recorded in prose is not enforcement; an infrastructure failure otherwise reddens a PR whose
   real gates are green, which teaches exactly the habit — red is negotiable — that the
   deterministic gates depend on not existing. **The placement is the whole requirement, and this
   decision originally got it wrong — see Amendment 1.**
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

## Amendment 1 (2026-07-25) — requirement 3 named a mechanism that does not do the job

Requirement 3 as adopted said a non-blocking lane "must carry `continue-on-error: true`", without
saying **where**. Both adopting repos put it on the **job**. That does not achieve the
requirement's own stated goal.

`jobs.<id>.continue-on-error` prevents a failing job from failing the **workflow run**.
`jobs.<id>.steps[*].continue-on-error` prevents a failing step from failing the **job**. Only the
second one governs the conclusion that GitHub publishes as a **check run** — and the check run is
what appears in the PR's checks list, what `gh pr checks` reads, and what a human sees as a red X.
Job-level placement greens the run while leaving the check red, which is precisely the
"infrastructure failure reddens a PR whose real gates are green" outcome the requirement exists to
prevent.

Measured on `defense-news-classifier` PR #123 (run `30141009937`), a Dependabot bump the action
refused with *"Workflow initiated by non-human actor"*:

| Surface | Conclusion |
|---|---|
| Workflow **run** (`actions/runs/30141009937`) | `success` |
| **Check run** `review` (what the PR shows) | **`failure`** |

`gh pr checks 123` printed `review fail` and exited 1. Every Dependabot PR in both adopting repos
carried a red X while both repos' ADRs asserted the PR stayed green.

**Corroboration this was a placement error, not a platform surprise:** `portfolio`'s review lane —
older than either adopting repo's, and not consulted when this decision was written — already put
`continue-on-error` on the action **step**, with an inline comment reading *"so the NEXT step
decides this job's colour."* The correct mechanism was in the system before this decision
generalised the wrong one. That is the finding worth keeping: **this decision was written from the
two newest instances and skipped the oldest**, and the oldest was the one that had already solved
requirement 3.

Two second-order notes:

- **A red X was the visible symptom; the invisible one is worse.** Because job-level placement
  greened the *run*, `gh run list --branch main` reported success — the surface a session
  pre-flight actually reads. This defect was self-concealing on exactly the check that would have
  caught it.
- **This is `SYS-021`'s own thesis turned on itself.** The decision says a green pipeline is never
  evidence that an agentic lane works. Requirement 3 was adopted on the strength of a green run
  conclusion and never verified against the check-run conclusion — the same class of error, one
  level up, in the decision that names the class.

**What changed:** requirement 3 now specifies step-level placement. Job-level `continue-on-error`
is not forbidden — it is a reasonable backstop for a non-step failure (runner death, a failing
`checkout`) and both repos keep it — but it does not satisfy requirement 3 on its own.

**Not claimed:** that step-level placement makes a lane unconditionally green. A lane may still
deliberately go red — `portfolio`'s classify step reddens when a tool denial *silenced* the review
(its `ADR-005`), which is a verdict about CI health, not about the PR. Requirement 3 governs
*accidental* red, not designed red.

## Downstream surfaces

- **`portfolio/.github/workflows/claude-review.yml` + `portfolio/decisions/ADR-005`** — **the
  oldest agentic lane in the system (2026-07-13), and omitted from this decision as adopted.**
  That omission is Amendment 1's root cause: this lane already placed `continue-on-error` on the
  step and routed the job's colour through a dedicated classify step, which is the requirement-3
  mechanism the two newer instances lacked. Counted here as an instance from now on; its `ADR-005`
  is the reference implementation. **`ADR-005` is not superseded** — it goes further than
  requirement 3 by distinguishing designed red from accidental red.
- **`defense-news-classifier/decisions/016-claude-code-action-pr-review.md`** — the source of all
  three original breaks. **Edited 2026-07-25** (Amendment 1): its Dependabot note asserted the run
  "reports success and the PR stays green", which the check-run conclusion contradicts.
- **`defense-news-classifier/.github/workflows/claude-review.yml`** — **amended 2026-07-25**:
  `continue-on-error` moved to the action step, bot actors skipped at the `if`. Was recorded as
  "compliant as of 2026-07-24" on the strength of a green run conclusion; that compliance claim was
  wrong for requirement 3.
- **`kb-agent/decisions/ADR-008` + `kb-agent/.github/workflows/claude-review.yml`** — second
  instance. **Both amended 2026-07-25**, same defect, same fix; its ADR carried the same
  "continue-on-error turns that exit-1 step into a green job" claim.
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
- **A second accepted hole, found by Amendment 1:** requirement 3 is verified by *reading the
  workflow file*, and reading it is what produced a wrong compliance claim for two repos. The
  check that would settle it mechanically is one line — `gh pr checks <n>` on a PR where the lane
  failed — but it needs a failure to exist, so it cannot run on demand. Nothing here asserts
  step-level placement; a future lane can regress it the same way. Named rather than papered over,
  per the `SYS-019` tension note above.
- **Revisit when:** a **fourth** agentic lane lands, or when one is ever promoted from advisory to
  gating. Gating changes the risk calculus entirely — a silently-muted *gate* is a hole in the
  build, not a missing opinion — and this decision does not authorise that promotion. (The
  third-lane trigger as written has already fired retroactively: `portfolio` was the third lane and
  predated the other two. Amendment 1 is that revisit.)

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **Leave it in `defense-news-classifier`'s ADR-016** | The three breaks are properties of agentic CI, not of that repo. Leaving it there means the second repo rediscovers them at the same cost, which is the drift `SYS-001` created this log to prevent. The trigger for promoting it was literally adopting the lane in `kb-agent`. |
| **Require a mechanical check that the artifact exists (full `SYS-019` treatment)** | Attractive and dishonest. "No comment posted" is ambiguous between *muted* and *nothing worth saying*, so any such check either fails on clean PRs or passes on muted ones. Asserting a guarantee the mechanism cannot deliver is worse than naming the bound — that is `SYS-019`'s own lesson about checks believed to cover more than they do. |
| **Ban agentic CI lanes; keep CI deterministic** | Overcorrects from three fixable configuration errors. The lane demonstrably produced a substantive, repo-specific review once configured. The property worth protecting is that *deterministic gates stay deterministic*, which requirement 3 secures directly. |
| **Make the review lane a gate so muteness would be conspicuous** | Inverts the risk: a non-deterministic reviewer with merge authority turns every model error into a blocked merge, and trains the habit of merging past red. It also would not have caught break 2 — a muted run exits 0, so it would have gated on nothing while appearing to gate. |
| **Rely on noticing that no comments ever appear** | This is what "unverified" means, stated as a plan. It is exactly how break 2 would have been found: eventually, by accident, after an unknown number of PRs went unreviewed while appearing reviewed. |
