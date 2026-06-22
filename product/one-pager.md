# Defense-News Intelligence — Product One-Pager

**Status:** Draft
**Date:** 2026-06-21
**Author:** San Lee

---

## What it is

A personal defense-news intelligence system: it ingests defense news, classifies it by
topic, stores it as a queryable knowledge base, and lets an agent answer questions over it.
*Ingestion → classification → knowledge base → agentic retrieval.*

## Who it's for

- **Primary user — defense-news analyst / researcher.** Must stay current across programs,
  contracts, geopolitics, and technology, and brief others on what matters. (Notional persona;
  defense is a deliberately chosen vertical, not a claim of domain expertise.)
- **Design partner — me, dogfooding.** First user and the early validation loop. The analyst
  is who the product is *designed for*; the dogfood is who it's *tested with*.

## Problem

Defense developments are scattered across many sources and arrive faster than one person can
triage. The analyst spends a disproportionate share of time *finding and sorting* — judging
relevance and assigning a category — before any real analysis begins. No lightweight, personal
system ingests the firehose, classifies by topic, and makes the result queryable, so the
analyst starts from a raw feed instead of a triaged knowledge base.

## Job-to-be-done

> When a stream of defense news comes in, help me quickly know **what matters** and
> **where it fits**, so I spend my time analyzing instead of sorting.

## How it works (and where the AI lives)

The system is also a deliberate tour of *how* AI is built and operated — each capability is a
distinct technique, demonstrated inside one coherent system rather than as scattered demos:

| Capability | AI technique | Repo |
|---|---|---|
| Categorize incoming news | LLM classification with an eval harness | `defense-news-classifier` |
| Store & serve the knowledge base | Domain service (REST, becoming event-driven) | `notes-api` |
| Answer questions over the KB | RAG + tool-use agent | `kb-agent` |
| Keep quality from regressing | Evals-as-CI | cross-repo (see roadmap) |

## Success metrics

**User-outcome (written for the analyst):**

- **Auto-triage rate** — share of incoming items correctly categorized automatically, so the
  analyst never hand-sorts them.
- **Coverage (recall)** — share of genuinely relevant developments the system surfaces rather
  than misses.
- **Answer usefulness** — for a query, the agent returns a correct, cited answer, fast.

**AI-quality (proves the system can be *measured*, not just demoed):**

- **Classification quality** — per-field precision / recall / F1. Baseline from the existing
  classifier eval: operational-domain **97.3%**; category **~79%**, with the ceiling set by
  *label ambiguity* (industry vs. procurement), not model horsepower — see `classifier/ADR-001`
  and `system/SYS-002`. *Update (v2): re-measured on real, human-labeled text, category is now
  **88.9%** (macro-F1 0.906) and operational-domain **88.9%** (macro-F1 0.894) — the ceiling is
  still label ambiguity, not model horsepower.*
- **Retrieval quality (RAG)** — recall@k, answer groundedness, citation correctness.
- **Agent task success** — pass rate on a fixed evaluation set.
- **Regression gate** — an eval pass-rate threshold wired into CI; a change that drops below it
  does not merge.

## Scope

**In (v1):** a defined source set; a fixed topic taxonomy; classify → store → query; agent
Q&A over the knowledge base.

**Non-goals (v1):**

- **Other verticals (e.g. banking).** The patterns are meant to generalize, but generalization
  is *articulated, not built* — one vehicle, done deeply.
- Custom model training / fine-tuning.
- Multi-user or real-time / high-throughput scale.
- UI polish.
