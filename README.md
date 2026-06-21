# Architecture

System-level architecture decisions and conventions for my projects — the place where
choices that span more than one repo are recorded and kept consistent.

The projects this covers:

- **[kb-agent](https://github.com/sanlee-ys/kb-agent)** — RAG + tool-use agent over my projects (the hub).
- **[defense-news-classifier](https://github.com/sanlee-ys/defense-news-classifier)** — LLM classifier with a real eval harness.
- **[notes-api](https://github.com/sanlee-ys/notes-api)** — Spring Boot 4 REST API (Java).
- **[learning-notes](https://github.com/sanlee-ys/learning-notes)** — plain-language notes on the concepts behind these projects.

## How decisions are organized

Decisions are recorded as **ADRs** (Architecture Decision Records) at two tiers, both using
the same template:

| Tier | Lives in | For |
|------|----------|-----|
| **Repo-local** | each repo's `decisions/` folder | choices scoped to a single repo (e.g. the [classifier's ADRs](https://github.com/sanlee-ys/defense-news-classifier/tree/main/decisions)) |
| **System** | this repo's [`decisions/`](decisions/) | choices that touch **two or more** repos |

**Numbering:** repo-local ADRs are `ADR-001…`; system ADRs here are `SYS-001…`. Cross-reference
across repos by prefixing — e.g. `classifier/ADR-003` or `system/SYS-001` — so a number is
never ambiguous.

## System Decision Log

| # | Title | Status |
|---|-------|--------|
| [SYS-001](decisions/SYS-001-record-architecture-decisions.md) | Record architecture decisions as two-tier ADRs | Accepted |
| [SYS-002](decisions/SYS-002-model-tier-standard.md) | Build on the Anthropic API; default to Sonnet, escalate to Opus only where it pays | Accepted |

## Writing a new ADR

1. Copy [`TEMPLATE.md`](TEMPLATE.md) to `decisions/SYS-00N-short-title.md` (next number).
2. Fill in **Context → Decision → Consequences → Alternatives Considered**.
3. Set the status — `Proposed` until it's actually adopted, then `Accepted`.
4. Add a row to the log table above.
