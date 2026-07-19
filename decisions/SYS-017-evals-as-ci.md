# SYS-017: Make evals-as-CI a system-wide pattern, gated on corpus provenance

**Status:** Proposed
**Date:** 2026-07-18
**Deciders:** San Lee

---

## Context

"Evals-as-CI" has been a named roadmap item since the early program docs, and it is **already
half-shipped** — the classifier wired its v2 gold evals into CI as a two-gate quality gate
([`classifier/ADR-007`](https://github.com/sanlee-ys/defense-news-classifier/blob/main/decisions/007-evals-as-ci-gate.md),
Accepted 2026-07-10). What it has never had is a system-level record. ADR-007 says so in its own
Context: it closes a gap "under the cross-repo SYS-007 'evals-as-CI' initiative" and explicitly
defers the roadmap bookkeeping as out of scope for a repo-local PR. That bookkeeping was never
picked up.

Three symptoms of the missing record, all found on 2026-07-18:

- **`SYS-007` is not the evals-as-CI decision.** It is the engineering-substrate and AI-skill map.
  ADR-007 cites it as one, and so did the documentation-portal decision (which instead said
  `SYS-003`) and `portal_src/telemetry.md` line 13. Three surfaces, two different wrong numbers,
  because there was no right number to cite. *(The portal decision was `SYS-008` when this was
  written; it is now [`ADR-001`](../adr/ADR-001-documentation-portal.md), and the citation there
  is corrected. Line numbers dropped — a locator into a file that is still being edited goes
  stale on its own.)*
- **`learning-notes/glossary.md` propagated the error into an agent-readable corpus.** It
  described evals-as-CI as an unbuilt milestone owned by SYS-007. `kb-agent` indexes that file,
  so the wrong citation was retrievable and speakable. Corrected in
  [learning-notes#38](https://github.com/sanlee-ys/learning-notes/pull/38).
- **A public surface overstates the state.** `portfolio/projects/product-and-program.html:113`
  claims evals-as-CI runs "across all three code repos." It runs in one.

The roadmap's **Next** item is "Evals-as-CI for `kb-agent`" (closing the rest of risk **R6**,
"RAG ships unmeasured"). Scoping that work surfaced a blocker that is not about CI plumbing at
all, and that is the substantive reason this ADR exists rather than being a pure bookkeeping fix.

**The blocker: `kb-agent`'s eval corpus is not reconstructible in CI.** The retrieval gold set
(`kb-agent/eval/gold_set.yaml`) is 27 hand-reviewed queries. **12 of them** (`note-01`–`note-10`,
`adv-01`, `adv-02`) declare `expected_sources` under `learning-notes/`. Those files are not in the
`kb-agent` repo. They are pulled at index time from a `notes_dirs` entry in `projects.yaml` whose
value is an **absolute Windows path** (`C:\Users\sanle\code\learning-notes`), resolved by
`scripts/index.py::notes_dirs()` from `REPO_ROOT / "projects.yaml"` with no environment override.
Only 15 files are committed under `kb/`. `chroma_db/` is generated and git-ignored.

So a gate wired up naively today would score **zero recall on 44% of the gold set** — not because
retrieval regressed, but because the documents are absent. It would be a red build that means
nothing, or worse, a floor set low enough to accommodate the absence, which silently redefines the
measured number.

## Decision

Adopt evals-as-CI as a **system-wide pattern**, and record **corpus provenance as a precondition**
of instantiating it anywhere.

### 1. The pattern

A measured quality number that is not enforced in CI is a report nobody re-checks, not a bar. Each
repo holding such a number instantiates the pattern with three parts, generalized from ADR-007:

- a **gate script** — a pure, machine-readable entry point that grades committed results against
  declared floors and exits non-zero on a breach (classifier: `src/eval_gate.py`);
- a **floors file** — thresholds that are **measured, never aspirational**, set below the current
  committed numbers by a margin sized to the eval's own run-to-run noise (classifier:
  `evals/thresholds.toml`);
- a **committed baseline** — the result snapshot the gate grades, refreshed only by a deliberate
  reviewed PR, never written back by CI.

### 2. One gate or two is decided by cost and determinism, not by convention

ADR-007 split the classifier's gate in two because its eval calls a paid, non-deterministic model,
and the repo is public (so a fork PR must never reach `ANTHROPIC_API_KEY`). That split is a
*response to those forces*, not the pattern itself.

`kb-agent`'s retrieval eval has neither force: `scripts/eval_retrieval.py` needs **no API key** and
embeds locally with `all-MiniLM-L6-v2`, so it is free and deterministic. **`kb-agent` therefore
gets one gate**, running on every push and pull request. Do not replicate the classifier's live/
scheduled job there; there is nothing paid to defer.

### 3. Corpus provenance is a precondition, and it is what unblocks `kb-agent`

**No eval may be promoted to a CI gate until its inputs are reconstructible in the CI environment
from version-controlled sources.** An eval whose corpus is partly absent does not measure worse
retrieval; it measures a missing filesystem, and any floor that tolerates it is a fiction.

For `kb-agent`, reconstruct rather than shrink: **shallow-clone `learning-notes` in the CI job**
and point the index at the clone. Precedent exists in this repo — `.github/workflows/portal.yml`
already shallow-clones `kb-agent`, `notes-api`, and `defense-news-classifier` as siblings to build
the portal. `learning-notes` is public, so no token is involved. This requires making the
`notes_dirs` source overridable (an env var read by `index.py`, or a CI-written `projects.yaml`),
since today it is a hard-coded absolute Windows path.

The order is therefore: **make the corpus reproducible → measure a baseline in that environment →
set floors from it → turn on the gate.** Not the reverse.

### 4. Containers are explicitly not the mechanism

A container image was considered as the way to make the `kb-agent` eval reproducible, since that
eval also depends on an ~80MB ONNX model and a built ChromaDB index. **Rejected as the load-bearing
mechanism**, because baking an index into an image does not answer where the index came from — it
relocates the provenance question without resolving it, and an opaque prebuilt index is a worse
answer than a scripted rebuild. `kb-agent`'s CI already caches `~/.cache/chroma` and
`~/.cache/huggingface`, which covers the model-download cost.

A container remains a legitimate **later optimization** — for pinning the embedding-model version
beyond what a cache key guarantees, and as shared substrate for the parked sandboxed-autonomy
experiment (`career/ideas.md`). It is deferred with an explicit trigger: adopt one if cache misses
or model-version drift actually make the gate flap. It is not a prerequisite for closing R6.

## Downstream surfaces

- ~~**`program/README.md`** — the roadmap's **Next** entry and risk **R6** both describe the
  `kb-agent` work; R6's "remaining piece" wording should name the corpus-provenance precondition,
  since that is now the actual blocking step. The roadmap page is generated from this section by
  `scripts/build_portal.py`, so this is the single edit point.~~ **Done 2026-07-19** — R6 now
  names the precondition, and its "CI runs across all three code repos" claim was corrected to
  one: the same overclaim this ADR caught on the portfolio had a second instance here, in the
  document that *records* the finding. R2 was restated at the same time; it was two versions
  stale.
- **`engineering/README.md`** — the keystone line ("finish evals-as-CI: a real golden set + judge,
  wired to fail a PR") predates the classifier pilot shipping; it reads as fully unbuilt.
- ~~**`README.md` decision-log table** — add a row for this ADR, **and for `SYS-016`**, which exists
  on disk and is cited from `engineering/README.md` and `SYS-007` but was never added to the table.
  The table currently stops at `SYS-015`, so it silently skips a number.~~ **Done** — the table now
  runs through `SYS-017` and carries a `Kind` column (2026-07-18).
- ~~**`SYS-008-documentation-portal.md:42`** — cites "`SYS-003` evals-as-CI". `SYS-003` is the
  agent-tool-layer contract. Repoint to this ADR.~~ **Done** — that decision was re-tiered to
  [`ADR-001`](../adr/ADR-001-documentation-portal.md) on 2026-07-18 and now cites this ADR.
- **`portal_src/telemetry.md:13`** — cites "evals-as-CI (`SYS-007`, the keystone)". Repoint here.
- **`classifier/ADR-007`** — remains canonical for the classifier's own two-gate design and is not
  superseded; its forward-reference to "the cross-repo SYS-007 evals-as-CI initiative" is the
  citation this ADR gives a real home.
- **`kb-agent`** — *(corrected 2026-07-19: this said the repo had **no `decisions/` directory**.
  It has seven ADRs, `ADR-001` through `ADR-007`.)* The instantiation work (gate script, floors
  file, CI job, `notes_dirs` override) should therefore land as a repo-local ADR in
  `kb-agent/decisions/`, citing this one — not ride this ADR as originally written.
- ~~**`portfolio/projects/product-and-program.html:113`** — states evals-as-CI runs "across all three
  code repos." False today; it runs in one. Public surface, so it should be corrected regardless of
  whether this ADR is accepted.~~ **Done** — corrected on the portfolio, and a *second* instance of
  the same overclaim was found and fixed in `program/README.md`'s risk R6 on 2026-07-19.
- ~~**`sanlee-ys/README.md:27`** — cites 88.9%, a v2-era number; `v3.0.0` shipped 92.6%. Adjacent
  staleness in the same public claim-surface, flagged not fixed here.~~ **Done** — the profile
  README now reads 92.6% / 92.6% / 87.0%. *Ticked 2026-07-19, having been fixed earlier without
  the box being checked: the mirror image of the failure this ADR records, and the reason
  `scripts/check_program_metrics.py` now enforces the numbers mechanically rather than by list.*
- **`learning-notes/glossary.md`** — already corrected in
  [learning-notes#38](https://github.com/sanlee-ys/learning-notes/pull/38). Listed because it is the
  surface that proved the citation rot reaches an agent-readable corpus.

## Consequences

- **Gives evals-as-CI a real number to cite**, which is the direct fix for three surfaces that
  invented one. Citation rot in a system with sixteen SYS docs is a predictable failure mode, and
  this ADR is partly a treatment of the symptom.
- **Closing R6 gets a correctly-ordered plan** instead of a plumbing task that would have produced
  a meaningless red build on first run. The corpus work is now visible as the real cost.
- **Names a precondition that generalizes.** Any future eval — `notes-api`, a scaled region eval,
  the rung-2 loop — inherits the same test: can CI reconstruct the inputs? This is the eval
  analogue of the frozen wire contracts (`SYS-004`/`SYS-005`/`SYS-006`).
- **What it costs:** the `notes_dirs` override plus a CI clone step is real work that the naive
  version would have skipped, and it makes `kb-agent`'s CI depend on a second repo being cloneable.
  If `learning-notes` were ever made private, the gate breaks and needs a token.
- **What it forecloses:** scoping the gate to only the reproducible queries. That option is
  deliberately closed below, and reopening it means re-reviewing the gold set, not just editing a
  filter.
- **This ADR is a decision, not a build.** No gate is wired by it. Marking R6 closed requires the
  `kb-agent` instantiation to actually land.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Scope the `kb-agent` gate to the 15 queries whose sources are committed under `kb/` | Silently discards 12 of 27 queries — the entire `notes` kind plus both `rag` adversarial pairs — from a gold set whose 8/5/10/4 composition was deliberately settled in `docs/notes/v2-kickoff.md`. The remaining number would still be called "retrieval recall" while measuring something narrower, which is exactly the dishonesty the eval exists to prevent. |
| Commit the `learning-notes` corpus into `kb-agent` | Reproducible, but forks the notes: the copy drifts from the source the moment either moves, and `kb-agent` becomes a second home for content it does not own. The drift would be invisible precisely because the eval would keep passing against the stale copy. |
| Commit a prebuilt `chroma_db/` index artifact | `chroma_db/` is git-ignored by existing convention, binary, and large. It would make the gate pass without proving the index *build* still works, which is a meaningful part of what the eval should protect. |
| Containerize the eval as the reproducibility mechanism | Does not answer corpus provenance — it packages whatever went in, so the "where did the notes come from" question survives inside the image, now harder to inspect. Kept as a deferred optimization with a trigger, not as the mechanism. |
| Replicate the classifier's two-gate split in `kb-agent` for symmetry | The split exists to manage paid, non-deterministic model calls and fork-PR secret exposure. `kb-agent`'s retrieval eval is free, local, and deterministic, so a scheduled paid job would be ceremony with no referent. |
| Fold this into `SYS-007` | `SYS-007` is the substrate and skill map; evals are one cluster on it. Three surfaces already mis-cite `SYS-007` *as* the evals decision, and merging them would ratify the confusion instead of fixing it. |
| Write nothing; let `classifier/ADR-007` stand as the record | It is repo-local by design and says so. It cannot carry a `kb-agent` precondition, and leaving it as the only record is what produced two different wrong SYS citations. |
