# SYS-002: Build on the Anthropic API; default to Sonnet, escalate to Opus only where it pays

**Status:** Accepted
**Date:** 2026-06-21
**Deciders:** sanlee

---

## Context

Multiple projects in this family make LLM calls (`defense-news-classifier`, `kb-agent`,
and anything new). Each could pick a provider and model on its own — and `defense-news-classifier`
already did, locally, in `classifier/ADR-001` (Anthropic + `claude-sonnet-4-6`). But "which
provider, which default model, and when do we pay for a bigger one" is a **house-wide**
question: re-deciding it per repo invites drift and silent overspend.

The eval evidence shapes the answer. On the classifier, category accuracy is capped at ~79%
by **label ambiguity** (industry vs. procurement is genuinely fuzzy), *not* by the model being
too weak — the operational-domain field already hits 97.3% on the same model. A bigger model
can't un-blur a fuzzy definition. So "always use the most capable model" would mostly buy
cost, not quality.

Current Anthropic lineup and pricing (per 1M tokens, input / output) at time of writing:

| Tier | Model ID | Input | Output | vs. Sonnet |
|------|----------|-------|--------|------------|
| Cheap | `claude-haiku-4-5` | $1 | $5 | ~0.33× |
| **Workhorse** | `claude-sonnet-4-6` | $3 | $15 | 1× |
| Escalation | `claude-opus-4-8` | $5 | $25 | ~1.7× |
| Top (rare) | `claude-fable-5` | $10 | $50 | ~3.3× |

## Decision

A cross-project **model-tier standard**:

- **Provider:** the Anthropic API across all AI projects.
- **Default workhorse:** `claude-sonnet-4-6` — strong instruction-following and tool use at
  the best cost/quality balance for these workloads.
- **Escalation tier:** `claude-opus-4-8`, used **only where an eval shows the quality gain
  pays** — e.g. low-confidence / boundary cases (the industry-vs-procurement edge), or as an
  **LLM judge** for grading real (non-synthetic) v2 data where an AI-made answer key no longer
  works. Opus runs on the slice that needs it, not on 100% of traffic.
- **Top tier:** `claude-fable-5` is reserved for genuinely hardest reasoning only; it is **not**
  a default (it's priced above Opus).
- **Pin exact model-ID strings** (no date suffixes, e.g. `claude-sonnet-4-6`, never
  `claude-sonnet-4-6-20251114`).

Principle: **model tier is a per-task cost/quality knob decided by the eval, not a default —
measure first, escalate only where it pays.** `classifier/ADR-001` is the first instance of
this standard; new repos inherit it.

## Consequences

- **One house default, referenced everywhere.** Repos point at this ADR instead of re-arguing
  the provider/model question; the classifier's local `ADR-001` is now the canonical example.
- **No silent overspend.** Opus is ~1.7× Sonnet; routing everything through Opus would overpay
  precisely where the ceiling is label ambiguity, not horsepower. Escalation stays evidence-gated.
- **Reproducibility.** Pinned IDs mean behavior doesn't shift under us when a new model ships.
- **A revisit obligation** (see below) — the standard is only honest if it's re-checked when
  the facts change. The triggers are written down so the decision reminds us, rather than us
  having to remember.

### When to revisit (escalation & review triggers)

Re-open this ADR (and record a superseding `SYS-NNN`) when **any** of these fire:

1. **An eval shows a model-limited ceiling.** A task's accuracy is capped by the model's
   reasoning — not by label ambiguity, bad data, or prompt — and a quick Opus A/B closes the
   gap. → escalate that task to Opus and note it here.
2. **The lineup changes.** A materially better or cheaper model ships, or a model this ADR
   names is **deprecated or retired**. (Anthropic publishes deprecation dates and a migration
   guide; model IDs and pricing do change over time — this is the most common trigger and the
   easiest to forget.) → re-baseline the default and the escalation target.
3. **A new task needs more reasoning than Sonnet handles well** (multi-step planning, long-horizon
   agentic work). → consider Opus/Fable for that task specifically.
4. **The cost profile shifts materially** (volume up, or relative pricing between tiers changes).

> Operational note to future-me / assistant: surface this ADR proactively when one of the above
> shows up in a session — e.g. an eval ceiling that looks model-limited, or news that
> `claude-sonnet-4-6` is being deprecated. The point of writing the triggers down is so the
> reminder doesn't depend on memory.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Default to Opus (or Fable) everywhere | Overpays ~1.7×–3.3× vs. Sonnet where the quality ceiling is label ambiguity, not model horsepower (per the classifier eval) — pay for capability the task can't use |
| Default to Haiku and escalate up | Too weak for nuanced label definitions and tool-use reliability; the floor would cost accuracy on the everyday path, not just the hard cases |
| Decide per repo, no house default | Drift and inconsistency across projects; the provider/model question gets re-argued each time |
| Pin "latest" / an alias instead of an exact ID | Non-reproducible — model behavior and tokenization shift silently underneath the projects |
| One frozen model forever, never revisit | Ignores deprecations and genuinely better/cheaper models; the revisit triggers above exist precisely to avoid this |
