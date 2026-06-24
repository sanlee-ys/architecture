# Architecture

System-level architecture decisions and conventions for my projects — the place where
choices that span more than one repo are recorded and kept consistent.

The projects this covers:

- **[kb-agent](https://github.com/sanlee-ys/kb-agent)** — RAG + tool-use agent over my projects (the hub).
- **[defense-news-classifier](https://github.com/sanlee-ys/defense-news-classifier)** — LLM classifier with a real eval harness.
- **[notes-api](https://github.com/sanlee-ys/notes-api)** — Spring Boot 4 REST API (Java).
- **[learning-notes](https://github.com/sanlee-ys/learning-notes)** — plain-language notes on the concepts behind these projects.

## Product context

What this system is *for* — the primary user, the problem, success metrics, and scope — lives in
the **[product one-pager](product/one-pager.md)**. The architecture decisions below are made in
service of it.

The **[program view](program/README.md)** holds the program-management layer — workstreams, a
dependency map, a Now/Next/Later roadmap, and a risk register.

The **[engineering view](engineering/README.md)** is the technical-craft companion — the AI-skill
substrate (`SYS-007`), the cross-repo engineering standards, and a reading map of where the depth lives.

The **[case study](case-study/README.md)** is the reflective companion — the decisions that shaped
the system and what the project demonstrates. It also carries an **external-validation** check — a
[trend-by-trend mapping](case-study/2026-agentic-coding-trends-mapping.md) of the system's practices
against Anthropic's 2026 Agentic Coding Trends Report.

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
| [SYS-003](decisions/SYS-003-agent-tool-layer-contract.md) | A contract for how kb-agent exposes and calls cross-system tools | Accepted |
| [SYS-004](decisions/SYS-004-classify-http-contract.md) | Freeze the /classify HTTP contract between the classifier and kb-agent | Accepted |
| [SYS-005](decisions/SYS-005-event-loop-contract.md) | Close the note-events loop — freeze the consume + tags-writeback contract | Accepted |
| [SYS-006](decisions/SYS-006-notes-read-contract.md) | Freeze the GET /notes read contract between kb-agent and notes-api | Accepted |
| [SYS-007](decisions/SYS-007-engineering-substrate-and-ai-skills.md) | Engineering is the substrate of the product & program tracks; an AI-skill map across all three | Accepted |
| [SYS-008](decisions/SYS-008-documentation-portal.md) | A generated documentation portal — one browsable view over the whole system | Accepted |

## Writing a new ADR

1. Copy [`TEMPLATE.md`](TEMPLATE.md) to `decisions/SYS-00N-short-title.md` (next number).
2. Fill in **Context → Decision → Consequences → Alternatives Considered**.
3. Set the status — `Proposed` until it's actually adopted, then `Accepted`.
4. Add a row to the log table above.
