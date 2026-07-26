# SYS-007: Engineering is the substrate of the product and program tracks — and the AI-skill map across all three

**Status:** Accepted
**Date:** 2026-06-22
**Deciders:** San Lee

---

## Context

The `architecture` repo has grown a career-exploration layer alongside its technical one. Two of
the three tracks already have real homes:

- **Product** — the [one-pager](../product/one-pager.md).
- **Program** — the [program view](../program/README.md): workstreams, dependency map,
  Now/Next/Later, risk register.
- A shared [vocabulary decoder](../reference/product-and-program-vocabulary.md) frames the whole
  thing explicitly as *"the SWE→PM/TPM exploration"* — read both columns, feel which one pulls.

Two gaps prompted this ADR.

**1. Engineering has no peer home — yet it's the root of the whole portfolio.** The build is
SWE-rooted (a classifier, an event-driven API, a tool-use agent), and the *"technical"* in TPM
rests entirely on that depth. The vocabulary doc already reaches for engineering (*"spec —
product = the PRD; engineering = the technical design"*) and has nowhere to point. Product and
program are documented as crafts; the craft they both sit on is left implicit.

**2. The tracks capture *classical* vocabulary, not the *AI-era* skills the system is actually
exercising.** The vocabulary doc teaches P0/MoSCoW, risk severity, JTBD — durable, necessary, and
pre-AI. But this system *is* a tour of post-2023 practice: an eval harness, a tool-use agent, RAG,
a model-tier standard, observability on the roadmap. The portfolio **builds** these and never
**names** them as a learning target — and an unarticulated skill doesn't transfer to a case
study or a technical conversation about the work.

The forces, from the north-star and the existing risk register: the goal is **one credible person
across three hats, not three disconnected personas** — so engineering must be positioned to
*reinforce* the P-tracks, not compete with them. And risks **R3 (breadth creep)** and **R4
(planning theater)** apply directly: this has to be a thin, living map tied to real artifacts, not
a hollow skills checklist.

## Decision

Two parts: a framing, and a map.

### 1. Engineering is the substrate, not a third parallel lane

The two P-tracks are differentiated by *what they do with engineering judgment, not by lacking it.*
Engineering is positioned as the **foundation both tracks draw on** and the **credibility floor for
"technical" PM/TPM** — not a competing third persona.

Concretely, engineering gets a peer `engineering/` path (established as the next step, mirroring
`program/`), but the framing is load-bearing: a reviewer should see engineering depth *under* the
P-tracks holding them up — the single-person, three-hats narrative the north-star needs.

### 2. Adopt an AI-skill map across all three tracks

The organizing meta-skill — the thing that's genuinely new and that nothing in the tracks names yet:

> **Every classical skill has an AI-era mutation, because outputs are now probabilistic.** Testing
> → evals. Spec → rubric. Project plan → milestone with a confidence interval. Monitoring → drift
> detection. Naming that mutation *per role* is the skill.

The map — six clusters (five at decision time; **Baselines & build-vs-buy** was added
2026-07-26, see Addenda), what each means per track, and **where it already lives in this system**
(grounding it in real artifacts, per house style, to keep R4 at bay):

| Skill cluster | Engineering (substrate) | Program (TPM) | Product (PM) | Already in the system |
|---|---|---|---|---|
| **Evals & quality bars** *(keystone)* | Golden sets, LLM-as-judge, regression gates in CI | Own the org-wide "good enough to ship" bar | Author the rubric — *what* "good" means | classifier eval (v2: 88.9% / 88.9%; v1 was 97.3% / ~79%); `SYS-003` eval gate; evals-as-CI (R6); the autonomy ladder's A/B/C split, where a held-out set the loop is never allowed to read **vetoed the loop's own best iteration** (`classifier/ADR-018`) |
| **Baselines & build-vs-buy** | Fit the classical model you are *not* going to ship, in order to price the one you are; paired significance tests instead of eyeballed deltas | Put a number under build-vs-buy before funding the expensive option | Decide whether the feature needs a model at all, or whether the cheap thing *is* the product | **Classical bake-off shipped** (`classifier/ADR-017`, 2026-07-25) — TF-IDF + logistic regression trained and scored against the same human gold set the LLM is scored on. The LLM wins 92.6% vs 72.2% on category and 92.6% vs 66.7% on domain, paired exact McNemar p=0.013 and p=0.0005, against a baseline that costs $0.00 and classifies the set in 4.8 ms. Rung 2 of the autonomy ladder then wrapped that same baseline (`classifier/ADR-018`) |
| **Context engineering & memory** | Window budgeting, retrieval, chunk/result caps | Plan context/data dependencies across teams | System prompt + memory as a versioned surface | `kb-agent` RAG; `SYS-003` rule 4 (context-budget discipline) |
| **Agents & orchestration** | Tool design, workflows-vs-agents, retries, HITL | Manage nondeterministic delivery (confidence, not dates) | Design for the failure case; trust & correction UX | `kb-agent` manual tool-use loop; `SYS-003` tool-layer contract; **the classifier's autonomy ladder, L1–L4, built and measured end to end** — two single-agent loops with an explicit done-signal (`classifier/ADR-005`, `ADR-018`) and a triage→classify→critic pipeline whose critic can hand a label *backward* (`classifier/ADR-020`). Both top rungs measured negative and were declined; see Addenda |
| **Observability, cost & reliability** | Tracing across agent steps, token/latency/drift | Capacity & inference unit-economics planning | Latency↔quality, cost-per-query as product calls | **OTel tracing shipped across all three services** — `kb-agent` loop, classifier `/classify`, `notes-api` enrichment seam (opt-in, GenAI/HTTP semconv — see Addenda); `SYS-002` model-tier; R7. Drift detection over the traces is the remaining leg |
| **Security, safety & governance** | Prompt injection, tool-exfiltration surface, output hardening | Responsible-AI review gates, launch risk | Transparency, uncertainty, kill-switches in UX | **Threat model documented** ([`SYS-016`](SYS-016-agent-tool-seam-threat-model.md), 2026-07-15) — the tool seam modeled as a regulated deployment; the tenancy + audit controls it names are roadmapped, not built |

**The keystone is evals.** It's the one cluster that exercises all three hats on a single
artifact — Eng implements it, Product authors the rubric, Program defends the bar — which is
exactly why evals-as-CI was the highest-leverage item in the program roadmap (now shipped for
the classifier, `classifier/ADR-007`; extending to `kb-agent` is Next).

**The genuinely-uncaptured skills** (new since ~2023; absent from the vocabulary doc):

- **Context engineering** — the successor to "prompt engineering"; the system does it (`SYS-003`
  rule 4) but never names it.
- **AI observability** — tracing/cost/drift for nondeterministic systems. **Shipped across the
  system 2026-07-15**: OpenTelemetry tracing over the `kb-agent` tool-use loop, the classifier
  `/classify` LLM call, and the `notes-api` enrichment seam (see Addenda). A named, exercised skill
  now, not a roadmap line; drift detection over the emitted traces is the remaining refinement.
- **AI security & governance** — prompt injection, the tool/HTTP exfiltration surface, output
  hardening. **Threat model now documented** ([`SYS-016`](SYS-016-agent-tool-seam-threat-model.md),
  2026-07-15): the agent tool seam modeled as a regulated deployment, crediting the `SYS-010`
  controls already in place and separating them from the tenancy + audit controls such a deploy
  would still need. The *documentation* hole is closed; those controls remain a roadmap, not a build.
- **MCP (Model Context Protocol) & interop** — the emerging standard for exactly the tool/context
  seam `SYS-003` solves with HTTP + `projects.yaml` today. **No longer a pure learning target:
  `kb-agent` now ships a working MCP server**, exposing `search_kb`/`list_projects` over **stdio,
  consumed directly by an MCP host** (Claude Code invokes it as a local subprocess). Three MCP
  integration patterns are architecturally distinct, and this doc should be precise about which one
  is actually implemented:
  1. **stdio, consumed by an MCP host** — the host spawns the server as a local subprocess and calls
     it over stdio. **This is what `kb-agent` implements today.**
  2. **Remote HTTP/SSE via the Messages API `mcp_connector`** — the model reaches a network-reachable
     MCP server directly. `kb-agent` does **not** support this: the connector requires the server be
     reachable over HTTP, and a stdio server can't be used this way without being re-exposed.
  3. **MCP tunnels** — a research-preview, heavyweight infra bridge from a local server up to
     Anthropic's hosted products. Not something `kb-agent` uses or needs.

  `kb-agent` implements **pattern 1 only**; patterns 2 and 3 remain future options, not current gaps.
  The candidate future ADR is correspondingly narrower now — *extend the kb-agent MCP seam to a remote
  transport (pattern 2)* — rather than *MCP-ify the seam from scratch*.

### What's next in "learning AI" (the learning sequence)

Rhymes with the delivery roadmap, but adds the uncaptured ones:

1. **Evals** (keystone) — evals-as-CI now has its first pilot: the classifier's real golden set + judge is wired into CI as an enforced gate (`classifier/ADR-007`). Extending the same pattern to `kb-agent`'s own RAG evals is next (program roadmap).
2. **Observability / OTel** — you can't improve what you can't see. **Shipped 2026-07-15** across
   all three services (`kb-agent` loop, classifier `/classify`, `notes-api` enrichment seam),
   opt-in per service with GenAI/HTTP semconv attributes. Drift detection over the traces is next.
3. **Context-engineering depth** — beyond naive RAG: retrieval quality, reranking, memory.
4. **AI security** *(threat model shipped)* — the threat model for the agent tool seam is
   documented ([`SYS-016`](SYS-016-agent-tool-seam-threat-model.md)); building its tenancy +
   audit controls is what a real regulated deployment would pick up next.

These four should be reflected back into the program view's Now/Next/Later (a `program/` edit,
follow-on) so the *delivery* plan and the *learning* plan stay in sync.

## Consequences

- **One foundation, three hats — the narrative the north-star needs.** A reviewer sees engineering
  depth holding up the P-tracks, not a third disconnected résumé.
- **The portfolio gains a named learning target,** not just artifacts — closing the "builds it but
  never articulates it" gap that would otherwise cost transfer in the capstone and any technical
  conversation about the work.
- **Evals are explicitly the keystone,** which independently justifies prioritizing evals-as-CI
  (already *Now*) as the single best cross-hat artifact.
- **The real gaps are surfaced and sequenced** — security especially, which had zero coverage and
  an actual exposure (the agent tool seam).
- **It costs living-doc upkeep** (R4). Mitigated: every cluster is tied to a real artifact, the map
  is deliberately thin, and the `engineering/` path + a vocabulary column are scoped as follow-ons,
  not sprawled here.
- **MCP is now demonstrated, not just aspirational.** `kb-agent` ships a working stdio MCP server
  (pattern 1 — consumed directly by an MCP host), so the capstone can claim *real* MCP experience,
  scoped honestly to that one pattern. Remote `mcp_connector` (pattern 2) and MCP tunnels (pattern 3)
  remain deliberate future options, not current gaps — precision here keeps the claim from
  overreaching in the other direction.
- **Low foreclosure.** If the "which column did you keep reading?" experiment ever pulls hard toward
  pure-PM and away from eng depth, the substrate framing is revisitable — but until that data lands,
  engineering stays strong, because it's what makes the rest credible.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Engineering as a third *parallel* lane (peer persona to product/program) | Splits the story into three disconnected personas; for a SWE→TPM arc the technical depth should sit *under* the P-tracks as their credibility floor, not compete for the same attention |
| Don't document it — keep building the skills | The system already builds evals/agents/RAG and never names them; an unarticulated skill doesn't transfer. Making the implicit explicit is the entire purpose of this repo |
| Put the AI-skill map in `learning-notes` | learning-notes is plain-language *concept* explainers (what RAG *is*); this is a cross-repo *career-framing decision with alternatives* — ADR-shaped, so it belongs in the system log (the same tier logic as `SYS-001`) |
| Ship one big "AI skills" checklist | Becomes planning theater (R4) — a hollow list that drifts from delivery; instead, a small set of clusters mapped to real artifacts, with "what's next" tied to the live roadmap |
| Fold engineering into the existing vocabulary doc only | That doc is a *terms decoder*, not a track home; engineering needs both a path dir (parity with the P-tracks) and its framing recorded as a decision — the vocab doc grows an engineering column as follow-on |

## Addendum — 2026-07-15: the observability cluster ships its first artifact

The **Observability, cost & reliability** cluster was the one marked "OTel (roadmap, Later)" at
decision time — built by the system (a model-tier standard, retries) but never *traced*. It now has
its first real artifact: **OpenTelemetry tracing over the `kb-agent` tool-use loop**
([kb-agent PR #39](https://github.com/sanlee-ys/kb-agent/pull/39)).

What shipped, and why it's the honest version of "closing" this gap:

- One `KBAgent.ask()` emits a span tree — `kb_agent.ask` → `chat <model>` (one per model call) →
  `execute_tool <name>` (one per tool call) — carrying OpenTelemetry **GenAI semantic-convention**
  attributes: `gen_ai.usage.{input,output,cache_read,cache_creation}_tokens`, per-tool latency (span
  duration) and the SYS-003 `status`, and the per-turn loop-pass count. This is precisely the
  "tracing across agent steps, token/latency/drift" the cluster named.
- **Opt-in, zero-overhead-when-off**: instrumented against the OTel *API* (no-op by default), the SDK
  configured only when `KB_AGENT_TRACING` is set. It doesn't tax the normal run or the offline suite.

**Status is `🔄 building`, not `✅ done`, on purpose.** The tool-use loop is instrumented; the two
HTTP services (`notes-api`, the classifier `/classify`) are not yet. The program view's *Later* item
("OTel observability across `notes-api` + `kb-agent`") accordingly narrows to the HTTP-service half.
The learning-sequence entry above moves from "pull it forward" to "in flight." (At the time of this
addendum the **AI security & governance** cluster was the one remaining `⬜ gap`; its threat model was
subsequently documented in [`SYS-016`](SYS-016-agent-tool-seam-threat-model.md) — see the next addendum.)

## Addendum — 2026-07-15 (later): tracing completed across all three services

The `🔄 building` above is now `✅ done` for the **tracing** leg of the cluster. The same pattern
shipped to both HTTP services, so the whole system is traced:

- **Classifier `/classify`** ([PR #76](https://github.com/sanlee-ys/defense-news-classifier/pull/76)) —
  `classify()` wraps its LLM call in a `chat <model>` span with GenAI-semconv token attributes and the
  resulting `{category, operational_domain}`. Opt-in via `CLASSIFIER_TRACING`; a no-op on the eval hot
  path so hundreds of calls per optimize iteration pay nothing.
- **`notes-api` enrichment seam** ([PR #34](https://github.com/sanlee-ys/notes-api/pull/34)) —
  `classify_and_writeback()` emits a `classify_and_writeback` task span with a child `POST /classify`
  span per HTTP attempt (HTTP semconv + `error.type`), so the cross-service hop and its retries are
  visible. Opt-in via `NOTES_API_TRACING`.

All three use the identical design — instrument against the OTel API always, configure the recording
SDK only behind a per-service env var, console exporter by default, OTLP as an optional extra — so the
services share one observability language. **What remains in the cluster is drift detection** over the
emitted traces (a refinement, not a gap), and **AI security & governance** was, at that point, the one
remaining `⬜ gap`.

## Addendum — 2026-07-15 (later still): the security cluster's threat model is documented

The last `⬜ gap` — **AI security & governance** — now has its documented artifact:
[`SYS-016`](SYS-016-agent-tool-seam-threat-model.md), a threat model for the agent tool seam written
as a *regulated-deployment* design exercise (OWASP-LLM-Top-10 + STRIDE, grounded in the real
`kb-agent` tool code). It credits the `SYS-010` controls already in place for six of eight threats
and isolates the two that only exist at the regulated boundary — **multi-tenant data isolation** and
**auditable access** — as a controls roadmap, with the `SYS-007` traces already named as the audit
substrate. Honest marker: the cluster moves from `⬜ gap` to **threat model documented; controls
roadmapped**, *not* `✅ done` — a documented threat model closes "no threat model," not "the controls
are built." With that, every cluster on the map is at least `🔄`; none is a bare `⬜`.

## Addendum — 2026-07-26: a sixth cluster, and the gap it closes

The map shipped with a blind spot that took a year to become visible: **all five clusters were
LLM-era.** Every one of them measures something about a language model or the system around it.
None of them asked whether the language model was the right tool, and the portfolio had the same
hole in the same shape — three measured-and-declined results
([`ADR-012`](https://github.com/sanlee-ys/defense-news-classifier/blob/main/decisions/012-retire-bm25-grounding.md)
grounding,
[`ADR-013`](https://github.com/sanlee-ys/defense-news-classifier/blob/main/decisions/013-decline-tiered-routing.md)
tiered routing, and judge-tier escalation in `faithfulness-judge`), each of them pricing a spend
*layered on top of* the LLM, none of them pricing the LLM itself.

That closed on 2026-07-25 with
[`classifier/ADR-017`](https://github.com/sanlee-ys/defense-news-classifier/blob/main/decisions/017-classical-baseline-bakeoff.md):
TF-IDF into logistic regression, trained on 300 judge-graded snippets and scored once against the
same 54 human-labeled rows the LLM is scored on. The LLM won decisively — 92.6% vs 72.2% on
category, 92.6% vs 66.7% on domain, paired exact McNemar at p=0.013 and p=0.0005 — against a
baseline that costs nothing and classifies the whole set in 4.8 ms. Frozen report:
[`evals/baseline_eval.txt`](https://github.com/sanlee-ys/defense-news-classifier/blob/main/evals/baseline_eval.txt).

**Why this is a cluster and not a footnote.** The naive framing is "San trained a model," which is
a checkbox. The transferable skill is narrower and more useful: *fit the classical model you are
not going to ship, in order to price the one you are.* That is the map's own meta-skill running in
reverse — the other five clusters are classical skills mutated by probabilistic outputs, and this
one is the classical skill kept intact deliberately, as the ruler. It also carries the per-track
split the map requires: engineering fits it and tests it properly (paired McNemar, not a delta
squinted at), program gets a number for build-vs-buy before funding the expensive option, and
product gets to ask whether the cheap thing is simply the product.

**The honest maturity marker is `✅ measured once`, not `✅ practice`.** One bake-off on one task is
an artifact, not a habit, and the experiment carried two disclosed handicaps that both cut against
the baseline: judge-generated training labels tested against human ones, and an `industry` class
with a single training row, structurally unlearnable. A margin that size survives them; they are
stated anyway, and both are on the public writeup rather than only in the repo.

**Also folded in: the autonomy ladder finished, and it belongs to the Agents & orchestration
cluster.** That row previously cited only `kb-agent`'s tool-use loop. The classifier now carries
L1–L4 built and measured end to end
([`ADR-018`](https://github.com/sanlee-ys/defense-news-classifier/blob/main/decisions/018-agent-driven-ml-loop.md),
[`ADR-020`](https://github.com/sanlee-ys/defense-news-classifier/blob/main/decisions/020-l4-multi-agent-pipeline.md),
shipped under `v3.1.0`), including the thing that actually distinguishes multi-agent work from a
pipeline with extra steps: a critic that hands a label *backward* for reclassification.

The result reads like a failure and is not one. Three of the four measurements came back negative —
an agent loop that improved the split it could see while degrading the held-out one, exemplar
retrieval that did nothing, and a multi-agent pipeline that produced this system's first
statistically significant *harm* at four times the cost. Every escalation the ladder offered was
declined with data, and the production path is still one well-prompted call. For the **Evals**
keystone that is the strongest available evidence: the held-out set vetoed the loop's own best
iteration, which is the Goodhart failure demonstrated rather than described.

**Sequencing note.** This addendum does not add a learning-sequence item. The sequence below lists
what to learn *next*; baselining was a gap in the *map*, not in the plan, and it was closed by the
work that revealed it. The remaining sequence is unchanged.
