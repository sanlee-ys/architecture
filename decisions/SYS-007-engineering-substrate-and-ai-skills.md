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

The map — five clusters, what each means per track, and **where it already lives in this system**
(grounding it in real artifacts, per house style, to keep R4 at bay):

| Skill cluster | Engineering (substrate) | Program (TPM) | Product (PM) | Already in the system |
|---|---|---|---|---|
| **Evals & quality bars** *(keystone)* | Golden sets, LLM-as-judge, regression gates in CI | Own the org-wide "good enough to ship" bar | Author the rubric — *what* "good" means | classifier eval (v2: 88.9% / 88.9%; v1 was 97.3% / ~79%); `SYS-003` eval gate; evals-as-CI (R6) |
| **Context engineering & memory** | Window budgeting, retrieval, chunk/result caps | Plan context/data dependencies across teams | System prompt + memory as a versioned surface | `kb-agent` RAG; `SYS-003` rule 4 (context-budget discipline) |
| **Agents & orchestration** | Tool design, workflows-vs-agents, retries, HITL | Manage nondeterministic delivery (confidence, not dates) | Design for the failure case; trust & correction UX | `kb-agent` manual tool-use loop; `SYS-003` tool-layer contract |
| **Observability, cost & reliability** | Tracing across agent steps, token/latency/drift | Capacity & inference unit-economics planning | Latency↔quality, cost-per-query as product calls | OTel (roadmap, Later); `SYS-002` model-tier; R7 |
| **Security, safety & governance** | Prompt injection, tool-exfiltration surface, output hardening | Responsible-AI review gates, launch risk | Transparency, uncertainty, kill-switches in UX | **Gap — nothing yet** (the `kb-agent` tool seam is the exposure) |

**The keystone is evals.** It's the one cluster that exercises all three hats on a single
artifact — Eng implements it, Product authors the rubric, Program defends the bar — which is
exactly why evals-as-CI is already the highest-leverage item in the program roadmap's *Now*.

**The genuinely-uncaptured skills** (new since ~2023; absent from the vocabulary doc):

- **Context engineering** — the successor to "prompt engineering"; the system does it (`SYS-003`
  rule 4) but never names it.
- **AI observability** — tracing/cost/drift for nondeterministic systems; on the roadmap as OTel,
  but not yet framed as a *skill*.
- **AI security & governance** — prompt injection, the tool/HTTP exfiltration surface, output
  hardening. **The real hole** — the system has an exposed agent tool seam and no documented
  threat model.
- **MCP (Model Context Protocol) & interop** — the emerging standard for exactly the tool/context
  seam `SYS-003` solves with HTTP + `projects.yaml` today. Named here as a learning target and a
  candidate future ADR (*MCP-ify the kb-agent seam*) — **not** a claim of current MCP experience;
  the system uses HTTP seams now.

### What's next in "learning AI" (the learning sequence)

Rhymes with the delivery roadmap, but adds the uncaptured ones:

1. **Evals** (keystone, in flight) — finish evals-as-CI with a real golden set + judge.
2. **Observability / OTel** — you can't improve what you can't see; pull it forward from *Later*
   as the next learning frontier.
3. **Context-engineering depth** — beyond naive RAG: retrieval quality, reranking, memory.
4. **AI security** — close the hole: a threat model for the agent tool seam.

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
- **MCP is a target, not a credential.** Stated plainly so the capstone doesn't overclaim; today's
  seam is HTTP, and MCP would be a deliberate future migration.
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
