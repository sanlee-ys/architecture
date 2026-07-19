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

- **Repo-local** decisions live in each repo's `decisions/` folder, for choices scoped to that
  one repo. The existing classifier log is the reference example. **The identifier is
  `ADR-NNN`** — that is what every heading and every citation uses. *Filenames* vary:
  `defense-news-classifier` and `faithfulness-judge` use a bare `NNN-` prefix, the others use
  `ADR-NNN-`. Both are fine and neither is worth renaming — the deviation is filename-only,
  every H1 and inbound citation already resolves, and renaming would break live public links
  to fix something no reader can see. *(Reconciled with practice 2026-07-18; this line
  previously mandated the `ADR-001…` filename form that 15 of 21 repo-local ADRs do not use.)*
- **System** decisions live in this `architecture` repo's `decisions/` folder (numbered
  `SYS-001…`), for choices that touch two or more repos.
- Both tiers use the same shape — Context → Decision → Consequences → Alternatives Considered
  → **Downstream surfaces** — with a Status / Date / Deciders header, captured in
  [`TEMPLATE.md`](../TEMPLATE.md) at the repo root. *(The fifth section was added to
  `TEMPLATE.md` by SYS-009 but never back-added to this list, so an author following this
  line literally produced a non-compliant document — which is why only 2 of 17 SYS docs carry
  it. Named here 2026-07-18; the rule is corrected rather than the 15 docs backfilled, since
  the fault was in the instruction.)*
- Cross-references are prefixed (`classifier/ADR-003`, `system/SYS-001`) so a number is never
  ambiguous across repos.

This document is `SYS-001`, recorded under the practice it describes.

### The promotion bar (amendment, 2026-07-18)

The original test — "does this touch two or more repos?" — has proven **necessary but not
sufficient**. Applied alone it admits conventions. A docstring style ([`SYS-014`](SYS-014-python-docstring-standard.md))
and a Pages deployment mechanism ([`SYS-012`](SYS-012-pages-actions-deployment.md)) both
technically span repos, and both now sit in the log at the same altitude as the frozen wire
contracts ([`SYS-004`](SYS-004-classify-http-contract.md), [`SYS-005`](SYS-005-event-loop-contract.md),
[`SYS-006`](SYS-006-notes-read-contract.md)). The log does not distinguish them.

> **Correction, 2026-07-18 (same day).** This paragraph originally continued: *"…whose
> breach fails a build. One is a lint setting; the others are load-bearing."* **That contrast
> is inverted on the evidence, and the examples were the wrong ones.** The "lint setting"
> fails builds in **three** repos — `defense-news-classifier/pyproject.toml`,
> `notes-api/pyproject.toml`, and `kb-agent/pyproject.toml` all select ruff's `"D"` rules
> with `convention = "google"`, and all three run `ruff check` in CI. Meanwhile `SYS-004`'s
> breach demonstrably did **not** fail a build: the classifier shipped `region` on
> 2026-07-18 with no coordinated consumer update and both suites stayed green (see the
> [`SYS-004` amendment](SYS-004-classify-http-contract.md)). Judged by "does a breach fail a
> build," the docstring standard outranks the wire contract — which is not an argument for
> demoting anything, it is proof that **enforcement is the wrong axis to sort a decision log
> by.** A decision's altitude is what it *forecloses*, not what currently happens to be
> wired into CI; enforcement is a property of this month's tooling, and it moved under this
> paragraph within hours of it being written. The bar in the next section stands as written
> — it tests foreclosure, correctly. Only this illustration was wrong, and it is left visible
> rather than rewritten because the log's credibility rests on it being safe to read what it
> actually said.
>
> The deeper reading, from the same audit: the bar has never rejected an entry, and both of
> its named examples pass it. That is not a sign the bar is too loose. `architecture` has no
> `ADR-*` namespace at all, and `kb-agent` and `portfolio` have no `decisions/` directory, so
> decisions about those repos have no floor to land on and arrive here by default. The log's
> size is a **missing lower tier**, not a permissive upper one.

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

~~**This is not retroactive.** `SYS-001`–`SYS-016` stand exactly as recorded; nothing is
renumbered, demoted, or superseded on account of a rule written after them.~~ **Narrowed
2026-07-18 (same day) — see below.**

> **Retroactivity is limited, not forbidden** *(narrowing, 2026-07-18)*.
>
> The original clause bundled two claims that came apart the moment the lower tiers landed.
> The first — *numbers already issued are not reused or renumbered* — is correct and stands:
> citations across every repo, the portal, and public surfaces point at those numbers, and
> churning them costs more than the inconsistency it corrects. The second — *nothing ever
> moves tier* — was never a principle. It was a description of there being nowhere to go.
> `architecture/adr/` did not exist when this was written.
>
> The rule, as narrowed:
>
> **Numbers already issued are not reused or renumbered, and every move leaves a tombstone at
> the original path so existing citations keep resolving. Published results that name a
> document are records, not indexes — they are footnoted, never rewritten. Within those
> constraints, an entry may be re-tiered when it fails the bar *and* a correct destination
> exists that did not exist when it was written. Absent such a destination, it stays.**
>
> That last conjunct carries the weight. It is why [`SYS-012`](SYS-012-pages-actions-deployment.md)
> stays — it binds two sibling repos and has no coherent home — and why
> [`SYS-016`](SYS-016-agent-tool-seam-threat-model.md) stays, its proposed destination being
> the wrong one. It encodes the *missing lower tier* as the trigger rather than opening the
> log to general revisionism.
>
> **Why this was narrowed rather than left alone.** An audit on 2026-07-18 proposed five
> demotions. Adversarial reviewers killed all five by citing this clause — a procedural
> objection, applied to a rule the owner had already authorized suspending, which meant the
> merits were never argued. Re-run on merits alone, three of the five moved: `SYS-008` and
> `SYS-011` fail prong 1 (they are this repo's own build features), and `SYS-014` fails prong
> 2 on its own testimony, describing itself as *"ratifying a de-facto standard, not imposing a
> new one."* A clause that blocks correct outcomes on procedure is doing the opposite of its
> job.
>
> **On the bar's record.** Until today it had never rejected an entry, which read as
> permissiveness. It was not: the bar was written on 2026-07-18 to govern prospectively and no
> new candidate had arrived, so "never rejected" was a statistic about zero trials. Applied
> retroactively to a hand-picked adversarial slate it rejects three of five. The bar has
> teeth; it had simply never been swung.

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
