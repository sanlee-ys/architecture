# SYS-011: A generated roadmap dashboard — RE-TIERED

**Status:** Moved — now [`architecture/ADR-002`](../adr/ADR-002-generated-roadmap-dashboard.md)
**Date:** 2026-06-30 (re-tiered 2026-07-18)
**Deciders:** San Lee

---

## This number is retired

The decision now lives at
[`adr/ADR-002-generated-roadmap-dashboard.md`](../adr/ADR-002-generated-roadmap-dashboard.md),
unchanged in substance. **`SYS-011` is never reused.**

This tombstone exists so every existing citation keeps resolving, per
[`SYS-001`](SYS-001-record-architecture-decisions.md)'s narrowed retroactivity rule.

## Why it moved

Source, parser, output and navigation are all inside this repo — `program/` is a directory
within `architecture`, not a sibling repo. The ADR guarantees no other repo gains an
obligation from it, and its single cross-boundary act is reading a version string from a clone
the portal already owns: consumption, not binding. The alternative it *rejected* — a
`roadmap.yaml` in every app repo — is the one that would have crossed repos.

Fails prong 1 of `SYS-001`'s promotion bar.

## A citation deliberately left alone

[`case-study/graphify-knowledge-graph-eval.md`](../case-study/graphify-knowledge-graph-eval.md)
records `"SYS-011 depends on SYS-008"` as the verified output of a paid knowledge-graph eval.
That is a **dated record of what an extractor found on a given day**, not an index of current
structure. It is footnoted, never rewritten — editing a published result to match a later
reorganisation would falsify the record it exists to be.
