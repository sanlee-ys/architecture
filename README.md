# Architecture

System-level architecture decisions and conventions for my projects — the place where
choices that span more than one repo are recorded and kept consistent.

The projects this covers:

- **[kb-agent](https://github.com/sanlee-ys/kb-agent)** — RAG + tool-use agent over my projects (the hub).
- **[defense-news-classifier](https://github.com/sanlee-ys/defense-news-classifier)** — LLM classifier with a real eval harness.
- **[notes-api](https://github.com/sanlee-ys/notes-api)** — Python/FastAPI notes REST API.
- **[learning-notes](https://github.com/sanlee-ys/learning-notes)** — plain-language notes on the concepts behind these projects, with an [interactive concept map](https://sanlee-ys.github.io/learning-notes/concept-map.html).

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

**New here, or not deep in the tech?** The **[learning-notes](https://github.com/sanlee-ys/learning-notes)** are the
plain-language companion to all of the above — what each term in these docs (RAG, tool-use, evals, event-driven
messaging…) actually means, in five short sections per idea. Start with the
**[interactive concept map](https://sanlee-ys.github.io/learning-notes/concept-map.html)** for a one-screen picture of
how the pieces connect, or read the **[notes site](https://sanlee-ys.github.io/learning-notes/)** in order. The
jargon-heavy docs link into the relevant note where a term first comes up.

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

**Kind** answers "what sort of decision is this," because the log flattens a docstring
convention and a frozen wire contract into identical-looking rows and a reader can't tell
which is which. It is *not* a ranking — a `Standard` can be more rigorously enforced than a
`Contract`, and currently is (see the [`SYS-001` correction](decisions/SYS-001-record-architecture-decisions.md)).

| Kind | Means |
|---|---|
| **Contract** | A frozen wire shape between two repos. Breaking it is an integration failure. |
| **Standard** | A binding rule applied across repos. |
| **Practice** | How the work itself is organised and recorded. |
| **Infra** | Build, deploy, and generation machinery. |
| **Security** | Trust model and threat analysis. |
| **Strategy** | Direction and framing rather than a technical constraint. |

| # | Kind | Title | Status |
|---|------|-------|--------|
| [SYS-001](decisions/SYS-001-record-architecture-decisions.md) | Practice | Record architecture decisions as two-tier ADRs | Accepted |
| [SYS-002](decisions/SYS-002-model-tier-standard.md) | Standard | Build on the Anthropic API; default to Sonnet, escalate to Opus only where it pays | Accepted |
| [SYS-003](decisions/SYS-003-agent-tool-layer-contract.md) | Contract | A contract for how kb-agent exposes and calls cross-system tools | Accepted |
| [SYS-004](decisions/SYS-004-classify-http-contract.md) | Contract | Freeze the /classify HTTP contract between the classifier and kb-agent | ⚠️ **Accepted — BREACHED** |
| [SYS-005](decisions/SYS-005-event-loop-contract.md) | Contract | Close the classify-and-writeback loop — freeze the BackgroundTask + tags-writeback contract | Accepted |
| [SYS-006](decisions/SYS-006-notes-read-contract.md) | Contract | Freeze the GET /notes read contract between kb-agent and notes-api | Accepted |
| [SYS-007](decisions/SYS-007-engineering-substrate-and-ai-skills.md) | Strategy | Engineering is the substrate of the product & program tracks; an AI-skill map across all three | Accepted |
| [SYS-008](decisions/SYS-008-documentation-portal.md) | Infra | A generated documentation portal — **re-tiered to [`ADR-001`](adr/ADR-001-documentation-portal.md)** | Moved |
| [SYS-009](decisions/SYS-009-documentation-cascade.md) | Practice | Cascade documentation by altitude — one body of work, a distinct artifact per surface | Accepted |
| [SYS-010](decisions/SYS-010-security-posture.md) | Security | Security posture — the local-service trust model and house security rules | Accepted |
| [SYS-011](decisions/SYS-011-generated-roadmap-dashboard.md) | Infra | A generated roadmap dashboard — **re-tiered to [`ADR-002`](adr/ADR-002-generated-roadmap-dashboard.md)** | Moved |
| [SYS-012](decisions/SYS-012-pages-actions-deployment.md) | Infra | GitHub Pages — deploy via Actions, not the legacy branch build | Accepted |
| [SYS-013](decisions/SYS-013-self-healing-by-default.md) | Standard | Design services to self-heal — detect and recover before a human has to | Accepted |
| [SYS-014](decisions/SYS-014-python-docstring-standard.md) | Standard | Google-style docstrings — **re-tiered to a house convention** ([`engineering/`](engineering/README.md)) | Moved |
| [SYS-015](decisions/SYS-015-public-claude-ops-repo.md) | Practice | Publish the Claude operating layer as a public repo (claude-ops) | Accepted |
| [SYS-016](decisions/SYS-016-agent-tool-seam-threat-model.md) | Security | Threat model for the agent tool seam — as a regulated deployment | Accepted |
| [SYS-017](decisions/SYS-017-evals-as-ci.md) | Standard | Make evals-as-CI a system-wide pattern, gated on corpus provenance | Proposed |
| [SYS-018](decisions/SYS-018-provider-owned-contract-artifacts.md) | Standard | Cross-repo contracts are enforced by a provider-owned artifact both sides assert against | Accepted |
| [SYS-019](decisions/SYS-019-assert-claims-dont-list-them.md) | Standard | Assert cross-repo claims against a generated artifact; a surface list is a prompt, not a guarantee | Accepted |

## Writing a new ADR

0. **Check it earns a number.** Per [`SYS-001`](decisions/SYS-001-record-architecture-decisions.md)'s
   promotion bar, a `SYS` entry must both **cross repo boundaries** and **foreclose something** — a
   real alternative existed and this closed it off. Crossing repos alone makes it a *convention*,
   which belongs in the binding repo's `CLAUDE.md`, not here. **If it binds only this repo, it is
   an `ADR-NNN` in [`adr/`](adr/), not a `SYS` number** — that tier exists precisely so
   architecture-local build decisions stop consuming system numbers.
1. Copy [`TEMPLATE.md`](TEMPLATE.md) to `decisions/SYS-00N-short-title.md` (next number).
2. Fill in **Context → Decision → Downstream surfaces → Consequences → Alternatives Considered**.
   `Downstream surfaces` is mandatory per [`TEMPLATE.md`](TEMPLATE.md) and `SYS-009` — "None" is a
   valid answer but must be written.
3. Set the status — `Proposed` until it's actually adopted, then `Accepted`.
4. Add a row to the log table above — and keep its **Status cell in sync with the document's own
   header** on every later status change. The two drifting apart is not cosmetic: `SYS-009` read
   `Proposed` in this table from 2026-06-29 to 2026-07-18 while the document itself said
   `Accepted`, and `SYS-016` was cited from two docs without ever having a row here.
