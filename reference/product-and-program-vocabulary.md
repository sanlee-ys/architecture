# Product & Program Vocabulary — a decoder

**Status:** Living
**Date:** 2026-06-22
**Author:** San Lee
**Purpose:** The working language of each track, grounded in our real artifacts — the
[product one-pager](../product/one-pager.md) (product) and the
[program view](../program/README.md) (program) — so you can *read and speak both* and feel which
one fits. This is a learning aid for the SWE→PM/TPM exploration, not a system doc.

**How to read it:** each term gets a plain definition · where it showed up in our work · the lens it reveals.

---

## 1. The priority language (the "P0 stuff")

Both tracks prioritize — but they prioritize **different things**, with **different words**. That
contrast is the single clearest signal of how the two crafts think.

### Product prioritizes *features*, by user value

| Term | Plain meaning | The test |
|---|---|---|
| **P0 / Must-have** | The thing is **not viable** without it. The MVP floor. | "If we cut this, does it still solve the core problem?" *No* → it's P0. |
| **P1 / Should-have** | Significantly improves it, but the core works without it. A fast-follow. | "Would we really *not ship* without this?" *We'd ship* → P1. |
| **P2 / Could-have / Future** | Explicitly out for v1, but documented so we don't make choices that **preclude** it. | "Architectural insurance" — guides design without being built. |

- **In our spec:** P0 = consume the event, reuse the classifier, idempotent writeback, no event loss,
  quality non-regression. P1 = dead-letter queue, low-confidence flagging. P2 = backfill, an LLM judge.
- **The discipline:** *be ruthless about P0.* "If everything is P0, nothing is." A tight must-have list
  is how you ship and learn fast.
- **MoSCoW** is the framework these map to: **Mu**st / **S**hould / **Co**uld / **W**on't-this-time.
- **Honest caveat:** the *numbers* (P0/P1/P2) aren't universal — some teams use P1 for "Should," others
  for "Could." The **ranking discipline** is what's real; the labels are a team convention.

### Program prioritizes *risk and delivery*, by what could kill you and what unblocks the most

| Term | Plain meaning | In our work |
|---|---|---|
| **Severity** (High/Med/Low) | How bad a **risk** is if it fires. Risks are ranked, not features. | R1 duplicate-processing = **High**; R2 accuracy ceiling = **Medium**. |
| **Likelihood × Impact** | The two axes that *produce* severity. | Implicit behind every severity in your register. |
| **Blocking vs non-blocking** | A dependency that **stops** downstream work vs one that doesn't. | The `notes-api` writeback seam is **blocking**; OTel is non-blocking. |
| **Load-bearing / critical path** | The dependencies the whole plan rests on. | Your own term: "the two load-bearing dependencies…" |
| **Now / Next / Later** | Roadmap **horizons** — commitment decreases as you go right. | The whole roadmap section of the program view. |
| **Milestone / phase gate** | A checkpoint that must pass before the next phase. | Phase 0 → 1 → 2 (classify-writeback loop → containers + local K8s → durable task queue). |

**The contrast that matters:** *Product asks "is it worth building?" (value). Program asks "what'll
kill us, and what has to come first?" (risk + sequence).* Same loop, two completely different questions.

---

## 2. Product-track terms (from the spec)

- **PRD / feature spec** — the doc that says *what we're building and why*, at product altitude (not *how*).
- **Persona** — a specific named user ("defense-news analyst"), not "a user." Specific enough to argue with.
- **JTBD (job-to-be-done)** — the outcome the user "hires" the product for: *"know what matters and where
  it fits, so I analyze instead of sort."* Describes the **need**, never the solution.
- **User story** — `As a [specific user], I want [capability], so that [benefit]`. The "so that" is the
  whole point; a story without a benefit is a task.
- **INVEST** — the test for a good story: **I**ndependent, **N**egotiable, **V**aluable, **E**stimable,
  **S**mall, **T**estable.
- **Acceptance criteria** — how you *prove* a requirement is met, often `Given / When / Then`. Covers the
  happy path **and** the error/edge cases (our R1 redelivery test is an acceptance criterion).
- **Goals vs non-goals** — outcomes you're chasing vs things you're *explicitly refusing to do this version*.
  Non-goals prevent scope creep and are as important as goals.
- **Leading vs lagging indicators** — metrics that move in days/weeks (adoption, completion, latency) vs
  ones that take weeks/months (retention, trust, revenue).
- **Success vs stretch target** — the "good enough to call it a win" number vs the "great" number.

---

## 3. Program-track terms (from the program view)

- **Workstream** — a parallel line of work, usually mapped to a team/repo (knowledge base, classification,
  agent…). Solo, your **repos are the workstreams**.
- **Dependency map** — the graph of what needs what before it can proceed. The thing program managers live in.
- **Risk register** — the tracked list of what could go wrong: each row has an **id (R#)**, **severity**,
  **mitigation / next action**, and an **owner / where it's tracked**.
- **Status cadence** — a *recurring* update (weekly status) "harvested from real progress." Cadence = the
  rhythm, not a one-off.
- **Stakeholder** — anyone who needs to *know* or *decide*, even if they're not doing the work. (Solo, your
  stakeholder is your future self / a portfolio reviewer — name it honestly.)
- **Phasing / milestone** — slicing a big delivery into gated stages so risk lands in chunks.
- **"Simulated program"** — *your own honest term*: a solo build has no real cross-team coordination, so the
  program layer is simulated. Naming the limit is more credible than faking it.

---

## 4. Jargon collisions to watch (you live in both worlds)

- **"RAG"** — in your *system*, **Retrieval-Augmented Generation** (`kb-agent`). In *program management*,
  **Red / Amber / Green** status health. Same three letters, opposite universes. This one *will* bite you.
- **"Roadmap"** — product means *prioritized bets* (what's worth doing); program means *sequenced delivery*
  (what order, given dependencies). Yours currently blends both in the program doc — you'll feel the seam.
- **"Spec"** — product = the PRD (what/why); engineering = the technical design (how). Keep the altitude clear.

---

## 5. The meta-point

As you read this back: **which column did you want to keep reading?** The product half (value, users,
the honest metric) or the program half (risk, sequence, what unblocks what)? That pull — not which one
*looks* more impressive — is the data point this whole exercise exists to collect.
