# SYS-001: Record architecture decisions as two-tier ADRs

**Status:** Accepted
**Date:** 2026-06-21
**Deciders:** sanlee

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

## Consequences

- **Cross-repo decisions finally have an owner.** The upcoming connect-the-repos and
  observability decisions have an obvious, discoverable home.
- **Consistency is cheap.** One template, copied; every ADR reads the same regardless of tier.
- **Decisions stay close to the code they bind.** Repo-scoped choices remain in their repo;
  only genuinely cross-cutting ones centralize here.
- **Small ongoing judgment cost:** each decision needs a one-second "is this one repo or the
  system?" call. The prefix convention keeps acting on the answer cheap.
- Existing classifier ADRs (001–004) are left exactly as they are — already consistent with
  this template.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Per-repo `decisions/` only | No home for cross-repo decisions; a kb-agent↔notes-api contract would be duplicated or hidden in one repo |
| One central log for *all* decisions | Divorces repo-scoped decisions from the code they affect; the classifier's local log would have to migrate and lose locality |
| `decisions/` folder inside learning-notes | Mixes technical ADRs with plain-language learner notes — different audience and tone in one place |
| Leave decisions in CLAUDE.md / commit messages | Not discoverable or reviewable as a set, and no status lifecycle (Proposed → Accepted → Superseded) |
