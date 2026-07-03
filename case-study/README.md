# Case Study — Building an AI System End to End

**Status:** Draft (grows as the build ships)
**Date:** 2026-06-21
**Author:** San Lee

A self-directed project to build a small but *production-shaped* AI system end to end — and,
just as deliberately, to show the **judgment** behind it. I'm a software engineer who moved into
product and am working toward **AI-focused technical program / product management**; this is the
worked example. The reflective companion to the in-world [product one-pager](../product/one-pager.md)
and [program view](../program/README.md).

## TL;DR

A defense-news intelligence system — ingest news, **classify** it, store it as a queryable
**knowledge base**, and let an **agent** answer questions over it. The point isn't the defense
domain (a deliberately chosen vertical, not a claim of expertise); it's a coherent tour of **how AI
is built and operated** — classification, RAG, tool-use agents, and evals — wired into one system
with the engineering and decision-making around it.

## The system at a glance

- **Where AI is applied:** one vertical (defense), gone deep. Generalization to others (e.g. banking)
  is *articulated, not built*.
- **How AI is used:** LLM classification with an eval harness → a knowledge-base service → a
  RAG + tool-use agent → evals-as-CI to keep quality from regressing.
- **The engineering around it:** async enrichment (FastAPI BackgroundTasks), container orchestration (K8s),
  observability (OTel), and two-tier architecture decision records.

See the [dependency map](../program/README.md#dependency-map) for how the pieces connect.

## Decisions that shaped it

The heart of the case study. Each row is a real tradeoff with the reasoning preserved — this is what
a two-tier ADR habit buys you.

| Decision | Why | Recorded in |
|---|---|---|
| Build on the Anthropic API; default to Sonnet, escalate to Opus only where an eval shows it pays | The classifier eval showed the accuracy ceiling was **label ambiguity, not model horsepower** — a bigger model would buy cost, not quality | `system/SYS-002` |
| Adopt a **tool-layer contract** for `kb-agent`'s cross-system tools (one observation shape + an error-recovery contract + an eval acceptance gate) | Once an agent calls *other repos'* services, tool shape and failure behavior become a system concern, not per-function style. **Distilled and *critically adapted* from an external skill bundle (ECC, MIT) — took two ideas, rejected the rest**; chose JSON for grader-friendliness and calibrated the source's "wrap every response" down to lean payloads. Now **implemented**: every tool returns the shape via `_success`/`_problem`, an `_obs()` grader enforces it in CI | `system/SYS-003` |
| **Freeze the `/classify` HTTP wire contract** between the classifier (provider) and `kb-agent` (consumer) — two-field response, pinned enums, 422/502 errors — with a breaking-change → MAJOR-bump + coordinated-update rule | Two repos on separate release cycles share a live HTTP seam; left implicit, a renamed field could mis-read at runtime with nothing failing. Freezing it + **contract tests on both sides** turns drift into a red build, and gives the roadmapped `v3.0.0` `region` field a gated path | `system/SYS-004` |
| Make `notes-api` **async** (vs. staying purely synchronous REST) | Motivates the classify-and-writeback seam *authentically* — a consumer (the classifier) needs to react to note changes; forces real reasoning about async decoupling via BackgroundTasks | `notes-api/ADR-001` |
| Extend `notes-api` in place; tag the REST baseline first | Most realistic, and ties into the system integration (`SYS-003`); tagging `v1-rest-baseline` preserves a clean REST reference to compare against | `notes-api/ADR-001`; tag shipped |
| **Close product + program gaps before deepening engineering** | Engineering credibility was already the strong half; the unmet gaps (program + product) are exactly what the target role screens for — do the harder, higher-leverage half first | [`program/README.md`](../program/README.md) |
| Idempotent tag writeback (handling at-least-once-style reprocessing) | _to be written in Phase 0 — see risk R1_ | ⬜ ADR pending |

## What this project exercises

| Area | Evidence |
|---|---|
| Systems & distributed design | Async enrichment via BackgroundTasks, K8s, the dependency map |
| AI fluency | Classification + eval harness, RAG + tool-use agent, model-tier reasoning (`SYS-002`, now implemented in `kb-agent`), an implemented tool-layer observation contract (`SYS-003`) and a frozen cross-service `/classify` contract (`SYS-004`), evals-as-CI |
| Decision-making under tradeoffs | Two-tier ADRs + the decision log above |
| Product framing | The [one-pager](../product/one-pager.md): user, problem, success metrics, non-goals |
| Program management | The [program view](../program/README.md): workstreams, dependencies, risk register, roadmap |
| Self-direction | Built solo, end to end |

## External validation

An outside yardstick now agrees with the judgment claims above: Anthropic's
[2026 Agentic Coding Trends Report](https://resources.anthropic.com/2026-agentic-coding-trends-report)
(gated; free sign-up) names, as industry trends, several practices this system had already adopted — the
integrator/conductor pattern, the **"delegation gap"** encoded as human-review guardrails, and
clean-room scope + a tool-layer contract. The full trend-by-trend mapping — including the places
the system *deliberately* diverges (it skips long-running autonomy on purpose) — is in
[`2026-agentic-coding-trends-mapping.md`](2026-agentic-coding-trends-mapping.md). Convergent, not
copied: the multi-session playbook it draws on was written after a real collision, not from the report.

## Tool evaluations

Third-party tools evaluated for adoption into this system, with credit and honest findings:

- [`graphify-knowledge-graph-eval.md`](graphify-knowledge-graph-eval.md) — evaluation of
  [graphify](https://github.com/safishamsi/graphify) (safishamsi, MIT) as a cross-repo knowledge
  graph, now wired in as an MCP server + per-repo git hooks.

## Honest limitations

Stated plainly, because naming them is more credible than hiding them — and the reasoning still holds:

- **Notional user.** The defense analyst persona is *reasoned*, not interviewed. Defense is a chosen
  vertical to demonstrate AI product thinking, not domain expertise.
- **Simulated program.** A solo project has no real cross-team coordination; the program layer is
  simulated, but the dependency, risk, and sequencing reasoning is real and transferable.
- **A known quality ceiling.** Classifier category accuracy is ~79%, capped by label ambiguity —
  documented and accepted (`system/SYS-002`), not papered over. *Update (v2): re-measured on real,
  human-labeled text, category is now 88.9% (macro-F1 0.906) and operational-domain 88.9% (macro-F1
  0.894) — the ceiling is still label ambiguity, not model horsepower.*

## Status & what's next

The product + program + narrative artifacts are in place, and **Phase 0 is underway**: `notes-api`
now fires a BackgroundTask on note creation that classifies the note and writes tags back
(`notes-api/ADR-001`, `system/SYS-005`). Next is hardening the idempotency path (R1) and
operational observability. This decision log grows with each real choice the build forces; a polished,
public-facing version of this case study may later graduate to a portfolio site.
