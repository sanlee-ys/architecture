# ADR-002: A generated roadmap dashboard — the whole system's status at a glance

**Status:** Accepted
**Date:** 2026-06-30 (re-tiered from `SYS-011` on 2026-07-18)
**Deciders:** San Lee

> **Re-tiered from `system/SYS-011`, 2026-07-18.** Source, parser, output and navigation are
> all in this repo — `program/` is a directory *inside* `architecture`, not a sibling. This
> ADR explicitly guarantees no other repo gains an obligation from it. The one cross-boundary
> act is reading a version string out of a clone the portal already owns, which is
> consumption, not binding. Notably the alternative it *rejected* — a `roadmap.yaml` in every
> app repo — is the one that would have crossed repos.
>
> Fails prong 1 of [`SYS-001`](../decisions/SYS-001-record-architecture-decisions.md)'s
> promotion bar. `SYS-011` remains as a tombstone at
> `decisions/SYS-011-generated-roadmap-dashboard.md`; the number is retired and never reused.
>
> **`case-study/graphify-knowledge-graph-eval.md` is deliberately not rewritten.** It records
> "SYS-011 depends on SYS-008" as the verified output of a paid knowledge-graph eval. That is
> a **dated record of what an extractor found**, not an index — footnoted, never edited.
> Rewriting a published result to match a later reorganisation would falsify the record.

---

## Context

`program/README.md` already hand-maintains a Now/Next/Later roadmap, tagged per workstream
(`**[classifier]**`, `**[notes-api]**`, etc.), alongside each app's live semver in its own
`pyproject.toml`. Reading "where does everything actually stand" today means opening that file,
cross-referencing three repos for their current version, and holding it all in your head — the
same problem `SYS-008` solved for documentation, not yet solved for status.

`SYS-008`'s Phase 2 (the interactive system map) answers *how the pieces connect*. This is a
different question: *what version is each piece at, and what's coming next* — a status board, not
a topology diagram. Worth its own decision because the naive approach (a new `roadmap.yaml` per
app repo, hand-filled) would duplicate `program/README.md`'s Now/Next/Later section, which is
already the curated, current source of truth. That's exactly the anti-pattern `SYS-008` named and
rejected for docs generally ("aggregate, never duplicate") — it applies here without modification.

## Decision

Extend `scripts/build_portal.py` to generate a **Roadmap** page from sources that already exist,
with zero new hand-authored files in any repo:

- **Version, per app:** read directly from each app's `pyproject.toml` (`project.version`) at
  build time. Never hand-typed into a second file — the portal's CI already clones `kb-agent`,
  `notes-api`, and `defense-news-classifier` as siblings, so the file is right there.
- **Roadmap items, per app:** parsed from `program/README.md`'s existing `## Roadmap — Now / Next
  / Later` section. Each bullet already carries a `**[tag]**` prefix (`classifier`, `notes-api`,
  `kb-agent`, or a cross-cutting tag like `product`/`program`/`ops`/`non-goal`); the parser groups
  by tag and bucket (Now/Next/Later). Bullets that don't map to one of the three app repos render
  in a separate "Cross-cutting & program" section below the app cards, not dropped.
- **Rendering:** a `portal/roadmap.md` page using MkDocs Material's grid-card layout (already used
  on the portal landing page — no new CSS/JS, no new plugin, holds the offline-first constraint
  `mkdocs.yml` already commits to). One card per app: name, live version badge, Now/Next/Later
  items. Wired into `mkdocs.yml` nav as a top-level entry, and linked from the landing page's "Jump
  in" grid alongside Decisions / System / Apps / Telemetry.
- **Authoring surface stays exactly what it is today.** Adding or moving a roadmap item is still
  "edit `program/README.md`" — nothing new to remember, nothing to keep in sync by hand.

## Consequences

- **The dashboard cannot drift from reality** — it has no state of its own to drift. A stale
  dashboard means a stale `program/README.md` or an unbumped `pyproject.toml`, which is the right
  place to fix it (same guarantee `SYS-008` gives for docs generally).
- **Zero new authoring habit.** No repo gains a `roadmap.yaml` to remember to update; the existing
  Now/Next/Later workflow is unchanged.
- **Couples the parser to `program/README.md`'s bullet format.** The `**[tag]**` prefix convention
  becomes load-bearing — a bullet written without it silently doesn't appear on the dashboard
  instead of erroring loudly. Accepted for v1; worth a lint check if it causes a real miss later.
- **Doesn't touch `SYS-008` Phase 2** (the interactive topology map). That's still open and answers
  a different question (how pieces connect vs. where they stand). This ADR only closes the
  status-board gap.
- **One more generated page to keep visually coherent** as the portal grows — mitigated by reusing
  the grid-card pattern already established on the landing page rather than introducing a new
  visual language.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **A `roadmap.yaml` per app repo, hand-curated** | Duplicates `program/README.md`'s Now/Next/Later section, which is already the curated source of truth. Adds a new file to remember to update in three repos for information that already exists in one. The exact anti-pattern `SYS-008` rejected for docs. |
| **Parse each app's `CHANGELOG.md` for "what's next"** | Changelogs record what *shipped*, not curated judgment about what's next or parked — that distinction can't be inferred from past entries, it has to be authored somewhere, and `program/README.md` already is that somewhere. |
| **Fetch version + roadmap over the GitHub API at build time (no local clone)** | The portal's CI already clones all three app repos as siblings for the docs aggregation step (`SYS-008`); reading local files is simpler and avoids a second network-dependent code path for the same data. |
| **A hand-crafted SVG status board, ported from the claude.ai visualize-tool style** | That style's CSS variables (`--surface-1`, `c-blue`, etc.) come from the claude.ai widget sandbox and don't exist in the portal's own stylesheet. Native MkDocs Material grid cards match the site's existing visual language and its offline-first, zero-external-request constraint. |
| **Render as a Mermaid diagram instead of grid cards** | Mermaid (already self-hosted and used for the dependency map) is better suited to graphs/flows than to a per-repo status board with variable-length item lists; grid cards read more naturally for "one card per thing, glanceable." |
