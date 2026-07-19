<!-- Copy this file to decisions/<PREFIX>-<NNN>-<short-title>.md.
     PREFIX is ADR for a repo-local log, or SYS for this system log.
     Delete this comment and the guidance lines once filled in. -->

# ADR-NNN: [Short imperative title]

**Status:** Proposed
**Date:** YYYY-MM-DD
**Deciders:** San Lee

---

## Context

What problem or decision point prompted this? What forces and constraints are at play
(deadlines, throughput, cost, team familiarity)?

## Decision

What was chosen. Name the mechanism, not just the intent.

## Downstream surfaces

Which surfaces restate or depend on what this decision changes — READMEs, portfolio copy,
sync registries, setup scripts, generated-doc sources? List them; the landing PR sweeps
them or files a fast-follow (SYS-009). "None" is a valid answer but must be written.

**This list is a prompt for a sweep, not a guarantee that one happened** (SYS-019). If a
surface restates a fact some repo publishes as an artifact — an eval number, a version, a
schema — generate it or assert it in CI instead. A list depends on someone reading it at
the end of the work, which is exactly when attention is lowest; that failure rate is not
zero, and on 2026-07-19 it was six claims across three repos.

## Consequences

- **What this makes easier.**
- **What it costs** — the tradeoff accepted.
- **What it forecloses**, or what we'll need to revisit later.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
|  |  |
