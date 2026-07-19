# Architecture-local decisions (`ADR-NNN`)

Repo-local decision records for the **`architecture` repo itself** — the portal build, the
dashboard generator, the deployment wiring, and anything else that binds only this repo.

## Why this exists

[`SYS-001`](../decisions/SYS-001-record-architecture-decisions.md) defines a two-tier practice:
cross-repo decisions get a `SYS-NNN` here, repo-local decisions get an `ADR-NNN` in the repo
they bind. Every other repo in the family had the second tier. This one did not — `decisions/`
held only `SYS-001…SYS-017` and there was no `ADR-*` namespace anywhere.

That gap had a cost, and it is the reason this directory exists. A decision about the
architecture repo's *own* machinery had no floor to land on, so it went up a tier by default.
[`SYS-008`](../decisions/SYS-008-documentation-portal.md) (the documentation portal) and
[`SYS-011`](../decisions/SYS-011-generated-roadmap-dashboard.md) (the roadmap dashboard) are
both build features of this repo occupying system numbers, not because anyone judged them
system-level but because there was nowhere else to put them.

A July 2026 audit of the full 38-document log found this was the main mechanism inflating the
`SYS` count. The log was not padded — it was **under-tiered**. The correction is additive: give
the repo the floor it was missing, so the next build decision lands here instead of upward.

## What goes here

- Portal generation, `mkdocs` config, `scripts/build_portal.py` behaviour
- The roadmap dashboard generator
- This repo's own CI and Pages deployment wiring
- Anything whose blast radius stops at this repo

## What does not

- Anything binding two or more repos → a `SYS-NNN` in [`decisions/`](../decisions/), subject
  to the promotion bar in `SYS-001` (crosses repos **and** forecloses something)
- Conventions that bind repos but foreclose nothing → the binding repo's `CLAUDE.md`

## Conventions

- Identifier is `ADR-NNN`; filenames follow `ADR-NNN-short-title.md`
- Same shape as the system tier — copy [`TEMPLATE.md`](../TEMPLATE.md) from the repo root
- Cross-tier references are prefixed so a number is never ambiguous: `system/SYS-004`,
  `architecture/ADR-001`, `classifier/ADR-012`

## Existing SYS entries are not being moved

`SYS-008` and `SYS-011` stay where they are. `SYS-001`'s non-retroactivity clause forbids
demoting them, and the citation cost is real — `SYS-008` alone carries 26 inbound references,
21 of them on public surfaces, and one published knowledge-graph eval records the edge
"SYS-011 depends on SYS-008" as a verified result. Renumbering to satisfy a rule written after
them would break more than it fixes. This tier changes what happens **next**, which is the only
thing it can change cheaply.
