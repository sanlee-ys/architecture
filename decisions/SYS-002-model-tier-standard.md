# SYS-002: Build on the Anthropic API; default to Sonnet, escalate to Opus only where it pays

**Status:** Accepted — revisit trigger fired 2026-07-11 (Claude Sonnet 5 shipped; see Amendment below — proposal only, pin unchanged)
**Date:** 2026-06-21
**Deciders:** San Lee

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

> **Update (v2):** Re-measured on real, human-labeled text, category accuracy is now 88.9%
> (macro-F1 0.906) and operational-domain 88.9% (macro-F1 0.894) — and the ceiling is still
> label ambiguity (industry vs. procurement), not model horsepower, so this decision holds.

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

## Amendment (2026-07-11) — Claude Sonnet 5 shipped; migration proposed, not decided

**Trigger fired:** revisit trigger (2) — "a better/cheaper model ships or `claude-sonnet-4-6`
is deprecated/retired." Claude Sonnet 5 (`claude-sonnet-5`) shipped 2026-06-30. `claude-sonnet-4-6`
is not deprecated by this — nothing forces a migration date — but the trigger is written down
precisely so a new option gets evaluated rather than ignored.

### The facts, as confirmed from Anthropic's release notes

- **Pricing:** introductory **$2/$10 per MTok through 2026-08-31**; standard price after that
  is **$3/$15 per MTok — identical to `claude-sonnet-4-6`'s steady-state price.** The "cheaper"
  framing only holds during the introductory window.
- **Context / output:** 1M token context window, 128K max output tokens — same ceiling as
  `claude-sonnet-4-6`.
- **Feature parity:** same tool/platform surface as `claude-sonnet-4-6`, with one exception —
  **Priority Tier is not available on Sonnet 5.**
- **New tokenizer:** produces **~30% more tokens for the same text** than `claude-sonnet-4-6`'s
  tokenizer (exact increase depends on content/workload shape). This is not a pricing change —
  it's a unit-cost change: the same request costs more in tokens even at identical $/MTok.
- **Sampling and thinking control removed:** adaptive thinking is on by default and **cannot be
  disabled** — manual extended-thinking budgets (`thinking: {type: "enabled", budget_tokens: N}`)
  are removed and return a 400. Setting `temperature`, `top_p`, or `top_k` to a non-default value
  also returns a 400 (same restriction as recent Opus versions). Both are behavioral changes, not
  just API surface — they remove two knobs the classifier and kb-agent evals may currently rely on
  (implicitly or explicitly) for reproducibility.
- **Not a differentiator:** structured outputs (`strict: true` / `output_config.format`) are GA on
  both `claude-sonnet-4-6` and Sonnet 5.

### The tradeoff, stated honestly

Sonnet 5 is **only cheaper on the sticker price, and only until 2026-08-31.** After that date it
costs the same per token as `claude-sonnet-4-6`. But "same price per token" does not mean "same
cost per request" — the new tokenizer's ~30% inflation means a workload that costs $X on
`claude-sonnet-4-6` today could cost roughly $1.30X on Sonnet 5 at steady-state pricing, before
any change in output quality is even considered. Whether Sonnet 5 nets out cheaper, roughly even,
or more expensive **depends on the workload's token shape** (prompt-to-output ratio, how much of
the prompt is cacheable, how verbose Sonnet 5's adaptive thinking turns out to be for these
specific tasks) — it is not knowable from the pricing table alone, only from re-running the
workload.

Separately from cost: `defense-news-classifier` and `kb-agent` are the two repos currently
pinning `claude-sonnet-4-6` (per this ADR's Decision section, unchanged below). Swapping either
repo's pin is not a drop-in replacement — adaptive thinking that can't be turned off and the
loss of manual sampling control mean model *behavior* differs, not just cost. Both repos would
need their eval thresholds re-baselined post-swap, the same way a model migration always requires
re-baselining under this ADR's existing principle ("measure first, escalate only where it pays"
— the same discipline applies to lateral moves, not just escalations).

### Proposal — awaiting San's sign-off, not a decision made here

This amendment records that the trigger fired and lays out the tradeoff; it does **not** decide
to migrate. Recommendation, offered as a starting point for San to approve, amend, or reject:

1. **The introductory-pricing window creates urgency to *decide*, not urgency to *migrate*.**
   `claude-sonnet-4-6` is not being deprecated by this trigger, so there is no forced date. The
   window closing 2026-08-31 mainly means: if a swap is going to happen opportunistically for the
   discount, that decision should be made before then — not that the swap itself needs to land
   before then.
2. **Evaluate before committing the pin change.** Run `defense-news-classifier`'s existing eval
   harness against Sonnet 5 (same eval set used for the v2 baseline referenced above) to get an
   actual before/after on accuracy, token cost, and latency — rather than reasoning from the
   pricing table alone. This is the same "measure first" discipline this ADR already commits to
   for escalation decisions; it applies equally to a lateral Sonnet→Sonnet swap.
3. **Do not swap `kb-agent`'s pin independently.** If the classifier eval shows Sonnet 5 nets out
   favorably, treat `kb-agent` as a second, separate re-baselining exercise — its workload shape
   (tool-use-heavy, per SYS-003) may see a different token-inflation profile than the classifier's
   more text-in/label-out shape.

**This is a call for San to approve, not a settled outcome.** If approved, the follow-up work is:
(a) run the classifier eval against `claude-sonnet-5`, (b) decide whether to swap based on the
result, (c) if swapping, update the pinned model string in this ADR's Decision section and open
the corresponding PRs in `defense-news-classifier` and `kb-agent` with re-baselined eval
thresholds. None of that follow-up work is done by this amendment.

## Addendum (2026-07-11) — implementation-level findings from reading the classifier source

The amendment above was written from Anthropic's release notes. This addendum records concrete,
code-level facts surfaced by directly reading `defense-news-classifier`'s source (and cross-checking
against Anthropic's classification use-case guide). It sharpens what "swapping the pin is not a
drop-in replacement" means in practice. **Same status as the amendment: additive documentation of an
open proposal. The `## Decision` section's pinned `claude-sonnet-4-6` string is unchanged.**

- **`temperature=0.0` is an actual breaking line, not a hypothetical.** `test_classify.py` and
  `stability.py` both call the API with `temperature=0.0` for determinism. Sonnet 5 (and Opus 4.7+)
  reject any non-default sampling parameter with an **HTTP 400** — so these are literal lines of code
  that fail on migration, not just a behavioral risk. `strict: true` already guarantees schema-valid
  output regardless of sampling, so determinism testing would need to shift to an empirical
  stability check (run N times, compare label agreement) rather than forcing it via temperature.

- **`effort` is the real replacement lever for the removed thinking budget.** Neither `classify.py`
  nor `gold_eval.py` sets `effort` today. On migration, both would silently inherit
  adaptive-thinking-**on**-by-default, rather than today's no-thinking-by-omission behavior — a
  behavior change, not just an API-surface change. Setting `effort` explicitly (likely `"low"`, for a
  short forced single-tool classification call) is the lever that recovers intended behavior; without
  it the migration silently changes how the model reasons on every call.

- **Refusal handling is a new, real branch to add.** Sonnet 5 is the first Sonnet-tier model with
  real-time cyber safeguards — refusals return `stop_reason: "refusal"` (**HTTP 200, not an error**).
  A defense-news domain is exactly the kind of content that could trip a false-positive decline that
  `claude-sonnet-4-6` never risked. A `refusal` branch should exist before cutover (tracked defensively
  regardless of migration timing) so downstream code doesn't choke on a missing `tool_use` block.

- **No deprecation pressure; the only clock is intro pricing.** `claude-sonnet-4-6` is not retiring
  before **2027-02-17**, so nothing forces a migration date. The only clock running is the
  introductory-pricing window (through **2026-08-31**) — and the ~30% tokenizer inflation is only
  partially offset by that discount if migration happens before the window closes, netting to roughly
  a wash after it. This reinforces the amendment's "urgency to *decide*, not to *migrate*" framing.

- **The classifier's tool-use is already ahead of the guide; one genuine unexplored technique.** The
  classifier's `strict: true` tool-use is *more rigorous* than Anthropic's own classification
  use-case guide (which parses plain XML-tag regex) — nothing to fix there. The one genuine advanced
  technique the guide uses that the classifier does not is embedding-based retrieval for hard cases
  (vs. the classifier's BM25). Frame this as a considered tradeoff worth one targeted eval slice, not
  a defect — Anthropic ships no first-party embeddings model, so adopting it would mean a new Voyage AI
  dependency, a real architectural change rather than a quick fix.

These findings do not change the recommendation in the amendment above (evaluate before committing the
pin change); they make the migration's actual code-level cost concrete. The pin change itself still
awaits San's sign-off and an eval-backed before/after, per the proposal above.
