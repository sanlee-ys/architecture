# SYS-003: A contract for how kb-agent exposes and calls cross-system tools

**Status:** Accepted
**Date:** 2026-06-21
**Deciders:** San Lee

---

## Context

`kb-agent` is the hub of this system: a manual Anthropic tool-use loop that answers
questions by calling tools rather than from prior knowledge. It already reaches across
repo boundaries — `classify_snippet` drives the `defense-news-classifier` service over
HTTP, and `notes-api` is the next service slated to become a tool. Once an agent is
calling *other repos'* services, "how a tool is shaped, what it returns, and how it
fails" stops being a `kb-agent`-local style question and becomes a **system** one:
every service that wants to be agent-callable has to meet the same bar, or the agent's
reliability degrades one inconsistent tool at a time.

So far the shape has been decided ad hoc, per function. That worked for three tools; it
won't hold as the seam widens. This ADR sets the contract once.

### What the current code already gets right

The existing `agent/tools.py` is the baseline, and it is mostly good — this ADR
formalizes its better instincts rather than replacing them:

- **Errors are returned, not raised.** `execute_tool` wraps every call so the model
  reads the failure and adapts on the next turn instead of the loop crashing.
- **The high-risk tool has a real recovery story.** `classify_snippet` (the only tool
  that crosses the network) distinguishes *no endpoint configured*, *service
  unreachable*, and *non-200*, and each message tells the model — and the user — how to
  fix it (e.g. the exact `uvicorn` command to start the service).
- **Tool descriptions are prescriptive about *when* to call.** The `TOOLS` schemas say
  "call this when the user wants X," which measurably improves tool selection.
- **The cross-service seam is HTTP, not an import**, so the repos stay decoupled.

### The gaps this ADR closes

- **No consistent observation shape.** Each tool returns a bespoke string. The model
  has to re-learn the format per tool, and there's no machine-checkable contract.
- **Success and empty paths carry no next step.** `search_kb`'s "No KB results for X"
  tells the model *what* happened but not *what to do* (broaden the query? drop the
  `kind` filter?). Recovery guidance exists only on the HTTP error paths.
- **There is no eval gate.** `kb-agent` has "no test suite and no CI" (its `CLAUDE.md`);
  the tool layer's reliability is currently asserted, not measured.

## Decision

Adopt a **tool-layer contract** that every agent-callable tool in this system must meet.
It has four design rules and one acceptance rule. The design rules are distilled from
ECC's `agent-harness-construction` skill (MIT — see *Source* below); the acceptance rule
applies this house's eval discipline (the classifier's harness, `classifier/ADR-001`) to
the agent itself.

**1. Action space — narrow, explicit, deterministic.**
Stable tool names; schema-first, minimal inputs; one job per tool; no catch-all tools.
Granularity follows risk: **micro-tools for high-risk operations** (anything crossing
the network or mutating state — `classify_snippet` today, any `notes-api` write
tomorrow), medium tools for read/search loops (`search_kb`, `list_projects`).

**2. Observation shape — one structure, every tool.**
Every tool result is a structured observation the model can act on without parsing prose:

| Field | Always? | Purpose |
|-------|---------|---------|
| `status` | yes | `success` \| `warning` \| `error` — the model branches on this |
| `summary` | yes | one line: what happened |
| `payload` | on success | the actual result (chunks, labels, list) |
| `source` | on success | provenance — the `[source: ...]` the system prompt already requires for grounding |
| `next_actions` | on `warning`/`error` | concrete follow-ups ("broaden the query", "drop the `kind` filter", "start the service with …") |

Format (JSON vs. a consistent labeled text block) is an implementation detail; the
*fields* are the contract. Keep success payloads lean — observation quality is about
actionability, not verbosity (it spends context budget; see rule 4).

**3. Error-recovery contract — every failure path carries three things.**
Root-cause hint, a safe retry/remediation instruction, and an explicit stop condition
(when to give up rather than loop). `classify_snippet` already does this; generalize it
to every tool, including the empty-result and not-indexed paths.

**4. Context-budget discipline.**
Cap and scope results (the existing `n_results` and ~1200-char chunk caps stay); cite
`source`; never dump a whole document when a chunk answers the question. Large guidance
lives in files the agent references, not inlined into every turn.

**5. Acceptance rule — the layer ships when an eval gate says so, not when it "looks right."**
Treat the tool layer like the classifier: evals are the unit tests of the agentic seam.
Using the grader taxonomy and metrics from ECC's `eval-harness` skill:

- **Code/rule graders (deterministic, cheap, run every time):** every tool result
  conforms to the observation shape; every error path contains a remediation line; every
  success carries a `source`. These are the regression spine.
- **Model grader (LLM-as-judge, used sparingly per [SYS-002](SYS-002-model-tier-standard.md)):**
  did the agent pick the *right* tool for the query, and is the answer grounded? Escalate
  the judge to Opus only on the slice where a cheaper grader can't decide.
- **Metrics:** `pass^3 = 1.0` on release-critical recovery paths (e.g. the
  "service unreachable" message must appear and be correct on every run); `pass@3 ≥ 0.90`
  on capability (correct tool selected). Track cost/latency alongside pass rate — a gate
  that ignores drift is how you ship a slower, pricier agent that still passes.

This is the substance the roadmap reserved for SYS-003 ("kb-agent calls notes-api +
classifier as tools"): the *seam* is HTTP and config-driven (endpoints live in
`projects.yaml`, not in code); the *contract above* is what makes each tool on that seam
trustworthy. `classify_snippet` is the first instance; `notes-api` inherits it when it's
wired up.

## Consequences

- **One bar, inherited not re-argued.** A new agent-callable service points at this ADR
  the way new repos point at SYS-002 — it knows what "agent-ready" means before writing
  the tool.
- **The model recovers instead of stalling.** Consistent `status` + `next_actions` on
  failure means the agent retries deliberately or stops cleanly, rather than looping to
  the `MAX_TOOL_ITERATIONS` cap on a dead service.
- **Reliability becomes measurable**, and feeds directly into the evals-as-CI roadmap
  item — the same gate that grades the classifier now grades the agent's tool layer.
- **It costs a refactor.** Today's tools return plain strings; adopting the observation
  shape touches every tool in `tools.py` and the `tool_result` handling in `agent.py`.
  The tradeoff is accepted: the change is small now (3 tools) and only gets more expensive
  as the seam widens, so paying it before `notes-api` lands is the cheap moment.
- **Guard against eval theater** (the `eval-harness` anti-patterns): don't overfit tool
  descriptions to known eval prompts, don't grade only the happy path, and don't let a
  flaky LLM judge into the release gate — keep the deterministic graders as the spine.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Keep deciding tool shape per function (status quo) | Worked for 3 tools; drifts into N inconsistent contracts as the seam widens — exactly the per-repo drift SYS-001/SYS-002 exist to prevent, one tool down |
| Adopt the full ECC harness/skill bundle wholesale | ~270 skills of one person's workflow; collides with this house's curated setup and conventions. Distill the 2 relevant ideas, leave the rest (this ADR *is* that distillation) |
| Wrap **every** response in the structured shape, success included, verbatim from the skill | Over-spends context on simple search hits; the contract keeps success payloads lean and reserves `next_actions` for warning/error paths where they earn their tokens |
| Switch to the SDK's built-in tool runner to get structure "for free" | `kb-agent` deliberately runs a manual tool-use loop for transparency (its `CLAUDE.md`); the contract is loop-agnostic and doesn't require giving that up |
| Ship the refactor without an eval gate | Reliability stays asserted, not measured — and an agent's tool layer is precisely where the same-model-writes-and-reviews blind spot bites; deterministic graders are the only thing that catches it |

---

*Source: design rules distilled from ECC's `agent-harness-construction` skill and the
acceptance rule from its `eval-harness` skill (github.com/affaan-m/ECC, MIT). Evaluated
and adapted to this system; the rest of that bundle was deliberately not adopted.*
