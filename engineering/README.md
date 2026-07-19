# Engineering View — Defense-News Intelligence

**Status:** Living
**Date:** 2026-06-22
**Author:** San Lee

The technical-craft companion to the [product one-pager](../product/one-pager.md) and the
[program view](../program/README.md). Per
[`SYS-007`](../decisions/SYS-007-engineering-substrate-and-ai-skills.md), engineering is the
**substrate** both P-tracks stand on — the credibility floor under "technical" PM/TPM — **not** a
third parallel lane. So this view captures the AI-era craft the system exercises, the standards that
make the repos cohere, and where the depth actually lives.

## The skill substrate — five clusters

The competency map from `SYS-007`. The meta-skill beneath all five: **every classical engineering
skill has an AI-era mutation, because outputs are probabilistic** — testing → evals, monitoring →
drift detection, integration test → eval gate.

| Cluster | What it means here | Where it lives | Maturity |
|---|---|---|---|
| **Evals & quality bars** *(keystone)* | golden sets, LLM-as-judge, regression gate in CI | classifier eval harness + gold set + validated judge, gating PRs (`classifier/ADR-007`); system-wide pattern proposed in `SYS-017` | ✅ shipped in the classifier, 🔄 extending to `kb-agent` |
| **Context engineering** | retrieval, chunk/result caps, grounding | `kb-agent` RAG; `SYS-003` rule 4 | ✅ in use (unnamed) |
| **Agents & orchestration** | tool design, the tool-use loop, error recovery | `kb-agent` loop; `SYS-003` tool-layer contract | ✅ shipped |
| **Observability, cost & reliability** | tracing, token/latency/drift, model-tier | OTel tracing across `kb-agent`, classifier `/classify`, `notes-api` (opt-in); `SYS-002` | ✅ tracing shipped |
| **Security, safety & governance** | prompt injection, tool-exfil surface, output hardening | threat model of the `kb-agent` tool seam as a regulated deploy (`SYS-016`); `SYS-010` posture | 📝 threat model documented |

## What's next — the learning sequence

Priority order. It rhymes with the program roadmap and adds the two skills the system uses or needs
but never named:

1. **Evals** (keystone, partly shipped) — the classifier has this: a 54-snippet hand-labelled gold set, a judge validated against it, and threshold gates that fail a PR (`classifier/ADR-007`). What remains is extending the pattern to `kb-agent`'s retrieval and settling `SYS-017`, which is still `Proposed`.
2. **Observability / OTel** *(shipped)* — OTel tracing across all three services (`kb-agent` loop, classifier `/classify`, `notes-api` enrichment seam), opt-in per service with GenAI/HTTP semconv attributes. Drift detection over the traces is the remaining refinement. You can't improve what you can't see.
3. **Context-engineering depth** — past naive RAG: retrieval quality, reranking, memory.
4. **AI security** *(threat model documented)* — the agent tool seam is modeled as a regulated deployment (`SYS-016`); building its tenancy + audit controls is the next step a real deployment would take.
5. **MCP / interop** *(stretch)* — candidate future ADR: MCP-ify the `SYS-003` HTTP seam. A learning target, not current practice.

## Cross-repo engineering standards

The house style every repo inherits — the conventions that make separate repos read as one system:

- **Two-tier ADRs** — decisions recorded, not lost (`SYS-001`). The habit *is* the craft.
- **Model-tier discipline** — Sonnet by default, Opus only where an eval shows it pays (`SYS-002`).
- **Tool-layer contract** — one observation shape + error-recovery + an eval gate for agent-callable tools (`SYS-003`).
- **Eval-as-acceptance** — a change ships when a gate says so, not when it "looks right."
- **Context-budget discipline** — cap and scope results, cite the source, never dump a document when a chunk answers.
- **Repo layout the portal depends on** — every app repo keeps `README.md`, `docs/` and
  `decisions/` **at its root, under exactly those names**. `scripts/build_portal.py` copies
  those three and nothing else (`APP_COPIED`, and the `for sub in ("docs", "decisions")` loop
  that skips silently via `if s.exists()`). Rename `decisions/` to `adrs/` in any repo and the
  portal drops that repo's entire decision log **with no error and no warning** — the build
  goes green and the content is simply gone.

  *Written down 2026-07-18, having previously existed only inside the build script.* This is a
  genuine cross-repo binding: it constrains six repos' directory layout, and it is the reason
  it did **not** ride down with the portal decision when that was re-tiered to
  [`ADR-001`](../adr/ADR-001-documentation-portal.md). A constraint recorded only in the code
  that enforces it is one nobody outside this repo can see — the same class of failure as a
  contract whose guard was never wired.

## Where the depth lives — a reading map

For going deeper (and for downtime reading) — the real artifacts, by repo:

| Repo | Read it for |
|---|---|
| [`defense-news-classifier`](https://github.com/sanlee-ys/defense-news-classifier) | the eval harness, the synthetic-data / circular-eval trap, the `/classify` service; ADRs 001–004 |
| [`kb-agent`](https://github.com/sanlee-ys/kb-agent) | the manual tool-use loop, RAG retrieval, the observation-shape refactor |
| [`notes-api`](https://github.com/sanlee-ys/notes-api) | Python/FastAPI REST API; SQLAlchemy 2.0 ORM; async tag enrichment via BackgroundTasks (CLASSIFIER_URL seam); `ADR-001`–`002` |
| [`architecture`](..) | the system decisions (`SYS-001`–`010`), the program view, the product one-pager, the case study |
| [`learning-notes`](https://github.com/sanlee-ys/learning-notes) | the plain-language concept behind each technique, and the D3 concept-map graph |

> **Note:** this table is the closest thing to a single reading surface today, and it's hand-kept. A
> *browsable* surface that stitches concepts + ADRs + program/product into one place — the concept
> graph has no node type for ADRs yet — is a tracked idea in the program view's *Later* and the case
> study's "portfolio site" line.
