# SYS-001: Record architecture decisions as two-tier ADRs

**Status:** Accepted (amended 2026-07-18: a promotion bar for what earns a SYS number)
**Date:** 2026-06-21 (amended 2026-07-18)
**Deciders:** San Lee

---

## Context

The projects (kb-agent, defense-news-classifier, notes-api, learning-notes) have grown into a
small family that is about to become a *connected system*: kb-agent will call notes-api and
defense-news-classifier as tools, and observability / eval conventions will span all of them.

Until now only `defense-news-classifier` recorded decisions — a clean `decisions/` log with
ADRs 001–004. The other repos had no convention, and, more importantly, **there was no home
for decisions that span more than one repo.** A service contract between kb-agent and
notes-api belongs to neither repo alone.

## Decision

Adopt a **two-tier ADR practice** with a single shared template:

- **Repo-local** decisions live in each repo's `decisions/` folder (numbered `ADR-001…`), for
  choices scoped to that one repo. The existing classifier log is the reference example.
- **System** decisions live in this `architecture` repo's `decisions/` folder (numbered
  `SYS-001…`), for choices that touch two or more repos.
- Both tiers use the same shape — Context → Decision → Consequences → Alternatives Considered,
  with a Status / Date / Deciders header — captured in `TEMPLATE.md`.
- Cross-references are prefixed (`classifier/ADR-003`, `system/SYS-001`) so a number is never
  ambiguous across repos.

This document is `SYS-001`, recorded under the practice it describes.

### The promotion bar (amendment, 2026-07-18)

The original test — "does this touch two or more repos?" — has proven **necessary but not
sufficient**. Applied alone it admits conventions. A docstring style ([`SYS-014`](SYS-014-python-docstring-standard.md))
and a Pages deployment mechanism ([`SYS-012`](SYS-012-pages-actions-deployment.md)) both
technically span repos, and both now sit in the log at the same altitude as the frozen wire
contracts ([`SYS-004`](SYS-004-classify-http-contract.md), [`SYS-005`](SYS-005-event-loop-contract.md),
[`SYS-006`](SYS-006-notes-read-contract.md)) whose breach fails a build. One is a lint setting;
the others are load-bearing. The log does not distinguish them.

Seventeen entries in, that flattening has a measured cost. All of the following were true on
2026-07-18:

- Three surfaces cited a **wrong SYS number** for evals-as-CI, two of them wrong differently:
  `SYS-008` said `SYS-003`, `portal_src/telemetry.md` said `SYS-007`, and
  `learning-notes/glossary.md` said `SYS-007` — the last inside a corpus `kb-agent` indexes and
  answers from. None of the three had a correct number to cite, because none existed.
- `SYS-016` was cited from `engineering/README.md` and `SYS-007` but had **no row in the log
  table**, so the table silently skipped a number.
- `SYS-009` had read **"Proposed" in the log table since 2026-06-29** while its own header said
  Accepted.

The common failure is not any one stale cell. It is that a registry stops being consulted once it
stops being legible, and citations start coming from memory. An agent indexing those files then
repeats the guess as fact.

**The bar, applying to new entries from 2026-07-18.** A decision earns a `SYS` number only when
**both** hold:

1. **It crosses repo boundaries** — the original test, unchanged.
2. **It forecloses something** — a real alternative existed and choosing this closed it off. The
   test is whether the *Alternatives Considered* table has entries that cost something. If every
   rejected option is a strawman, this is not a decision; it is a preference being written up.

If only (1) holds, it is a **convention**, not a decision. Conventions are still written down —
in the house conventions doc when they bind several repos, or in the binding repo's `CLAUDE.md`
when they bind one. They simply do not consume a number in a log whose entire value is that every
entry is load-bearing.

**This is not retroactive.** `SYS-001`–`SYS-016` stand exactly as recorded; nothing is renumbered,
demoted, or superseded on account of a rule written after them. Citations across every repo,
the portal, and the public surfaces point at those numbers, and churning them to satisfy a later
rule would cost more than the inconsistency it corrects. The bar governs what gets added next.

## Consequences

- **Cross-repo decisions finally have an owner.** The upcoming connect-the-repos and
  observability decisions have an obvious, discoverable home.
- **Consistency is cheap.** One template, copied; every ADR reads the same regardless of tier.
- **Decisions stay close to the code they bind.** Repo-scoped choices remain in their repo;
  only genuinely cross-cutting ones centralize here.
- **Small ongoing judgment cost:** each decision needs a one-second "is this one repo or the
  system?" call. The prefix convention keeps acting on the answer cheap.
- **That judgment call is now two questions, not one** (2026-07-18 amendment): crosses repos
  *and* forecloses something. The added cost is one honest look at the Alternatives table before
  claiming a number — paid at authoring time, when the author still knows whether the rejected
  options were real. What it buys is a log where the number itself carries weight, which is the
  only property that makes citing one worth doing.
- Existing classifier ADRs (001–004) are left exactly as they are — already consistent with
  this template.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Per-repo `decisions/` only | No home for cross-repo decisions; a kb-agent↔notes-api contract would be duplicated or hidden in one repo |
| One central log for *all* decisions | Divorces repo-scoped decisions from the code they affect; the classifier's local log would have to migrate and lose locality |
| `decisions/` folder inside learning-notes | Mixes technical ADRs with plain-language learner notes — different audience and tone in one place |
| Leave decisions in CLAUDE.md / commit messages | Not discoverable or reviewable as a set, and no status lifecycle (Proposed → Accepted → Superseded) |
