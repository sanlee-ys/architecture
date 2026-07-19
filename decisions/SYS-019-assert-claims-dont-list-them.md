# SYS-019: Assert cross-repo claims against a generated artifact; a surface list is a prompt, not a guarantee

**Status:** Accepted
**Date:** 2026-07-19
**Deciders:** San Lee

---

## Context

`SYS-009` established that one body of work cascades across surfaces, and `TEMPLATE.md`
requires every decision to list its **Downstream surfaces**. Both are good rules. Neither
prevented what happened on 2026-07-18/19.

**Six drifted claims, found by hand, across three repos in one day:**

| Surface | Claim | Reality |
|---|---|---|
| `portfolio/index.html`, résumé | category 88.9% / domain 94.4% | 94.4% / 92.6% — two prompt changes stale |
| `program/README.md` R2 | 88.9% (v2) | 92.6% (v3.0.0) |
| `product/one-pager.md` | 88.9% (v2) | 92.6% |
| `case-study/README.md` | 88.9% (v2) | 92.6% |
| `portfolio/README.md` | 88.9% / 94.4% | 92.6% / 92.6% |
| `program/README.md` roadmap | classifier at v2.0.0; v2.1.0 under **Next** | v3.0.0; v2.1.0 shipped 2026-07-17 |

Every one was found by a person grepping, and **twice the sweep was declared complete
before it was** — once after checking a single file, once after fixing three of five.

The tempting diagnosis is carelessness, and it is wrong. Look at the last row. The
`v2.1.0` release genuinely had no `Downstream surfaces` section naming `program/README.md`
— so the rule "list your surfaces" would have helped. But now suppose it *had* been
listed. The next release still depends on somebody reading that list, at the end of the
work, and acting on it. **A list is an instruction to a human at the exact moment
attention is lowest.** Its failure rate is not zero and never will be.

Meanwhile the same class of claim on the same repos, once wired to an artifact, has not
drifted at all: `SYS-018`'s provider-owned `/classify` schema turned a silent breaking
change into a red build the same week it was introduced.

The distinguishing property is not "which surface" or "how disciplined the author." It is
whether the claim **has a machine-readable source of truth to be compared against**.

## Decision

**Where a claim restates a fact that some repo already publishes as a generated artifact,
that claim must be asserted against the artifact mechanically. A `Downstream surfaces`
list remains required, but it is a prompt for a human sweep — it is never the guarantee.**

Concretely, three tiers, strongest first:

1. **Generate, don't restate.** If the surface lives in the repo that owns the artifact,
   render the claim from it and check the rendering in CI. It then has no state of its own
   to drift — `architecture/ADR-002`'s argument. *(Instance: the classifier's README
   headline table, `scripts/gen_readme_metrics.py --check`.)*
2. **Assert, if the surface is elsewhere.** Mark the claim and fail CI when it diverges
   from the fetched artifact. *(Instances: `portfolio/scripts/check-published-metrics.cjs`,
   `architecture/scripts/check_program_metrics.py`,
   `learning-notes/scripts/check_published_metrics.py`.)*
3. **List, only when neither is possible.** A `Downstream surfaces` entry, understood as a
   sweep prompt with a real failure rate — not as coverage.

**A guarantee names its enforcer** (`SYS-009`'s amendment). Under this decision, a sentence
asserting a current fact about another repo is either enforced or it is a dated
observation. There is no third state where it is "kept in sync."

**Three properties every such check must have**, each learned from a check that lacked it:

- **Fail on liveness, not just on mismatch.** Zero markers found is a failure, and so is
  zero of a given marker *type*: a version check that matched nothing sat behind sixteen
  healthy metric markers and reported OK against injected drift.
- **Warn-and-pass on fetch failure.** A provider outage must not redden an unrelated
  build; drift is loud when the artifact is reachable, and that is the accepted bound.
- **Ratchet what is not covered, and say so.** Unmarked claims are counted against an
  allowance that may only shrink, and the check reports how many it is *not* checking.

## Downstream surfaces

- **`engineering/README.md`** — the "Published figures are asserted, never retyped"
  standard is the convention half of this decision; it now cites this ADR as the rule it
  instantiates. Already written 2026-07-19.
- **`TEMPLATE.md`** — the `Downstream surfaces` guidance is reworded to say what the
  section is *for*, so authors stop reading it as a guarantee.
- **The four existing checks** (classifier generator, portfolio, architecture,
  learning-notes) are this ADR's instances; no change needed, they are the evidence.
- **`SYS-009`** — complementary, not superseded. It still governs how work cascades; this
  narrows what may be *claimed* about the result.
- **`SYS-017`, `SYS-018`** — `SYS-018` is the same move applied to wire contracts and is
  the direct precedent. `SYS-017` is unaffected.
- **The grandfathered ADR ratchets** (`classifier` 14/15, `notes-api` 2/2) — deliberately
  **not** backfilled. Backfilling would produce lists, and this decision's whole point is
  that lists are the weaker instrument. They tighten as new ADRs land.
- **`README.md`** decision-log table — row added.

## Consequences

- **Makes easier:** answering "is this claim true?" without reading anything. Four repos'
  worth of published numbers and version claims are now enforced at 47+ marked sites.
- **Costs:** every new outward claim needs a marker, and every new artifact-owning repo
  needs a small checker. The convention is centralised in `engineering/README.md`; the
  implementations are deliberately **not** shared, because a vendored guard that falls out
  of sync reports green from stale logic — worse than duplicating 130 lines.
- **Forecloses:** "we'll remember to sweep" as an acceptable answer for any claim that has
  an artifact. It is still the only available answer for claims that don't — prose about
  design intent, teaching notes, dated records — and those stay explicitly out of scope.
- **Revisit when:** a fifth checker appears. At that point the duplication argument flips
  and a shared package (or the seam registry already deferred) earns its keep.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **Backfill `Downstream surfaces` into the 16 grandfathered ADRs** | Produces lists, and the whole finding is that lists don't hold. It also means writing surface lists for decisions nobody present made — guessing — and a fabricated list is worse than an absent one because it reads as though someone checked. |
| **A release checklist ("sweep downstream before tagging")** | Same instrument as a list, one layer up, with the same dependence on attention at the end of the work. It would not have caught the roadmap drift, which is a *doc* that went stale between releases, not at one. |
| **A scheduled cross-repo drift sweep (weekly job)** | Detects drift late rather than preventing it, and the failing surface is a report nobody owns. Useful as a backstop for un-artifacted claims; not a substitute for a build that goes red. |
| **One shared checker package vendored into every repo** | A guard that falls out of sync reports green from stale logic — false coverage, the exact failure mode this ADR exists to remove. Revisit at five instances. |
| **Do nothing; treat 2026-07-19 as an unusually bad day** | Six claims, three repos, two premature "sweep complete" calls, and one guard (`portfolio`) that was green throughout because its scope was narrower than its claim surface. That is a systemic property, not a bad day. |
