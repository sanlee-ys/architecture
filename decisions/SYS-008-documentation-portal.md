# SYS-008: A generated documentation portal — RE-TIERED

**Status:** Moved — now [`architecture/ADR-001`](../adr/ADR-001-documentation-portal.md)
**Date:** 2026-06-23 (re-tiered 2026-07-18)
**Deciders:** San Lee

---

## This number is retired

The decision now lives at
[`adr/ADR-001-documentation-portal.md`](../adr/ADR-001-documentation-portal.md), unchanged in
substance. **`SYS-008` is never reused.**

This tombstone exists so every existing citation keeps resolving —
[`SYS-001`](SYS-001-record-architecture-decisions.md)'s narrowed retroactivity rule requires a
move to leave one, precisely so that re-tiering costs a redirect rather than a broken link.

## Why it moved

The portal is a build feature of the `architecture` repo. It **reads** six repos; it does not
bind them, and the ADR argues that as a feature rather than a limitation. Under `SYS-001`'s
promotion bar it fails prong 1 — crossing repo boundaries.

It only ever carried a system number because this repo had no `adr/` namespace to land in.
That is the mechanism the 2026-07-18 audit named: the log was **under-tiered, not padded**.

## What did not move

`scripts/build_portal.py` imposes an unwritten cross-repo layout expectation — every app repo
must keep `README.md`, `docs/` and `decisions/` at its root under exactly those names, or the
portal drops that content silently. That constraint *is* system-level and was lifted into
[`engineering/README.md`](../engineering/README.md) in the same change, rather than riding
down into a repo-local ADR where nothing outside this repo would see it.
