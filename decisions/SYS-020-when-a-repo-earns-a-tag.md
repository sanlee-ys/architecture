# SYS-020: A repo earns tags when it publishes a number or exposes a contract

**Status:** Accepted
**Date:** 2026-07-19
**Deciders:** San Lee

**Related:** [`SYS-004`](SYS-004-classify-http-contract.md) (the `/classify` contract),
[`SYS-018`](SYS-018-provider-owned-contract-artifacts.md) (provider-owned contract
artifacts), [`SYS-017`](SYS-017-evals-as-ci.md) (evals as CI).

---

## Context

A status sweep on 2026-07-19 checked every repo's tags and releases against what its prose
claimed had shipped. The result: **`defense-news-classifier` carries 7 tags and 5 GitHub
releases; twelve other repos carry no releases at all, and six carry no tags either.**

That is not automatically wrong — most of those repos genuinely do not need versions. The
problem is that **the absence is indistinguishable from an oversight.** The classifier has a
documented semver policy, a CHANGELOG, and a tag per milestone. Every other repo has nothing
and says nothing about why. A reader — including a future session running a sweep — cannot
tell "deliberately continuous" from "nobody got around to it," so the sweep flags it every
time and the flag is noise.

Two of those untagged repos carry a real cost, not just ambiguity:

**Published numbers with no anchor.** `faithfulness-judge` states κ = 0.751 (Opus) and 0.716
(Sonnet) at n=189. `kb-agent` publishes retrieval eval numbers. Neither repo can answer
"which commit produced that?" This is the same failure the published-metrics guard chain
exists to prevent, one layer down: assertions are checked against a metrics file, but nothing
anchors *which state of the repo* produced the metrics file.

**Contracts with nothing to pin.** [`SYS-018`](SYS-018-provider-owned-contract-artifacts.md)
records what happens when a contract moves without coordination — the classifier shipped
`v3.0.0` with a new `region` field and `kb-agent` read a two-field response for the rest of
the day, no build red on either side. A consumer that wants to pin a known-good provider
state needs the provider to *have* states. Tags are the cheapest form of that.

## Decision

**A repo gets tags when it publishes a number or exposes a contract another repo depends on.
Every other repo is deliberately untagged, and that decision is recorded here so its absence
of tags reads as intent rather than neglect.**

### Tagged

| Repo | Why |
|---|---|
| `defense-news-classifier` | Both: publishes eval numbers, provides the `/classify` contract. Already compliant — semver + CHANGELOG + release per milestone. **This repo's existing practice is the reference implementation.** |
| `faithfulness-judge` | Publishes κ figures that appear in portfolio copy. A cited number needs a commit behind it. |
| `kb-agent` | Both: publishes retrieval eval numbers, and consumes/exposes the SYS-004 contract. |
| `notes-api` | Exposes the notes read contract (`SYS-006`) that kb-agent's `search_notes` calls. |

### Deliberately untagged

| Repos | Why |
|---|---|
| `learning-notes`, `learning-notes-site`, `portfolio`, `sanlee-ys` | Continuously published content. Nobody pins a version of a website; a tag would encode nothing a reader could use. |
| `dotfiles`, `claude-ops`, `architecture` | Always-latest by design. Tagging an operating layer implies a stable release you could deliberately hold back on, which is the opposite of what [claude-ops ADR-002](https://github.com/sanlee-ys/claude-ops/blob/main/decisions/ADR-002-claude-ops-canonical.md) makes these repos — public-first and canonical *now*. |
| `career`, `finance`, `job-tracker`, `github-follow-tracker`, `training` | Personal tooling with no external consumer and no published figures. Nothing to reproduce, nothing to pin. |

### The rule, stated for future repos

When a new repo appears, ask two questions:

1. **Does anything outside this repo quote a number it produces?** If yes, tag — the number
   needs a commit behind it.
2. **Does another repo call it, import it, or assert against its shape?** If yes, tag — the
   consumer needs something to pin.

If both answers are no, leave it untagged and do not treat that as debt.

## Consequences

**What this makes easier**
- A missing tag becomes readable. Sweeps and fresh sessions can consult this table instead of
  re-flagging eleven repos as gaps every run.
- Published figures become reproducible. "κ = 0.751" gains an answer to "from what?"
- Consumers gain something to pin, which is the precondition for the coordinated-update
  discipline `SYS-018` asks for.

**What it costs**
- Two versioning schemes now coexist in the house. The classifier's semver is a genuine
  contract promise; a tag on `faithfulness-judge` is closer to a bookmark. That is acceptable
  — they are answering different questions — but the distinction should not blur into
  "everything must be semver."
- Tagging is a manual step that will be forgotten. This ADR does not add automation, and a
  tag that lags reality is a smaller problem than the ambiguity it replaces, but it is not
  zero.

**What it forecloses / revisit triggers**
Revisit if a content repo ever gains a consumer — e.g. if something starts importing
`learning-notes` content programmatically rather than reading it — or if a personal-tooling
repo starts publishing figures. The rule is about consumers and claims, not about repo size
or effort invested.

## Alternatives considered

| Option | Reason not chosen |
|---|---|
| Tag every repo, uniformly | Manufactures ceremony for repos where a version number means nothing. A tag on a notes site is a lie about how it is consumed. |
| Tag nothing but the classifier; leave the rest undocumented | The status quo. It works until something asks "which commit produced this number", and it makes every sweep re-litigate the same eleven repos. |
| Date-stamp releases instead of semver everywhere | Loses the compatibility promise where it genuinely matters (`/classify`, notes read). Semver is doing real work in exactly the places this ADR keeps it. |
