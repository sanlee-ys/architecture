# SYS-017: Make evals-as-CI a system-wide pattern, gated on corpus provenance

**Status:** Accepted — adopted 2026-08-02 with the tier ladder in the adoption amendment
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
- **Adoption (2026-08-02) added surfaces of its own** — the status change ripples into every page
  that described this decision as unratified. They are listed in the adoption amendment's own
  Downstream surfaces block below rather than mixed in here, so the July sweep stays readable as
  the July sweep.

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

---

## Adoption amendment (2026-08-02) — the tier ladder, where the fleet actually sits, and what moves next

This decision sat at `Proposed` for fifteen days. Adopting it is this amendment, and two gaps in
the original are why it was easy to leave unratified:

1. **It named a finished state, not rungs.** "Instantiate the pattern with three parts" describes
   a repo that already has a gate. It gives a repo with none of them nothing to aim at *next*, and
   it gives a reader no vocabulary for saying what a repo has *today* without reading its CI.
2. **It placed two repos and inferred the rest.** The classifier was the pilot, `kb-agent` was the
   blocked case, and nobody ever asked where `faithfulness-judge`, `notes-api` or `learning-notes`
   stood. Two of those three turn out to have no eval at all, which is the right answer for them —
   but that was an assumption, not a finding.

So this amendment adds a **ladder** and a **table of where each repo actually stands**, both read
off the workflow files on disk on 2026-08-02 rather than off the roadmap's description of them.
Nothing below changes the original Decision; §1–§4 stand as written, and §3 (corpus provenance)
becomes the ladder's entry condition rather than a `kb-agent` footnote.

### The principle, in one line

**A measured capability claim needs a gate that actually runs.** Everything below is that sentence
made checkable. Four house corollaries, each earned from a specific failure rather than assumed:

- **Floors come from measured runs, with run-to-run noise under them — never from aspiration.**
  The classifier states this as a house rule in `classifier/ADR-014` ("thresholds after
  measurement, never before"), and the sharpest instance is a *refusal*: its scaled region run
  produced no threshold at all, because a single pass is a dated measurement and cannot supply the
  noise band a floor sits above. `src/scale_region_eval.py` declines to propose one in code, not
  just in prose. A floor invented before the measurement is not a bar; it is a number the eval will
  be tuned to meet.
- **A gate that cannot fail is theater.** Every guard in this system that survived contact has a
  liveness clause: `eval_gate.py` refuses to grade a snapshot whose row count shrank rather than
  scoring the smaller sample; a missing provenance sidecar is a failure and not a skip, or `rm` is
  a one-command bypass; `check_program_metrics.py` fails on *zero* markers, because a check that
  verifies nothing reads exactly like a check that passed. The reason this keeps needing restating
  is that all three failure modes are **green**.
- **The split between legs is decided by cost and determinism, not by convention.** Offline,
  deterministic, keyless legs run on every push and pull request. Legs that spend money run only
  on an owner-initiated event — the classifier's live lane is reachable from `workflow_dispatch`
  and `schedule` only, which means a fork pull request has no event that can invoke it at all.
  The corollary runs the other way too, and the original §2 already says so: a repo with nothing
  paid to defer gets **one** leg, not a ceremonial second one.
- **Harness health is a separate output from the finding.** A clean lift computed over a run that
  dropped a third of its rows is not a finding. The reusable shape already exists in-house
  (`paired_compare.py`, vendored into more than one repo): scored / errored / unscored / unscorable
  counted separately, zero-count reasons emitted so that a clean run and an unexamined one do not
  render identically, and metrics computed only over rows where every arm scored — never imputed,
  never counted as a miss. And it must be **enforced, not printed**: the classifier's A/B harness
  had this rule as decision criterion #4, printed it, did not assert it, and produced a well-formed
  report over an interrupted arm.

### The ladder

Four rungs. Each is a strict superset of the one below, and each is defined by a mechanism a
reader can point at in a file — not by intent.

| Tier | The repo has | How you tell from outside |
|---|---|---|
| **0 — Measured, not gated** | A runnable eval harness, and possibly a committed result. CI runs tests and lint. | No workflow step invokes the harness. The published number is a dated report. |
| **1 — The eval runs in CI on every PR** | The harness executes on `push`/`pull_request`, offline and keyless, and reports. Merge is not blocked by the value. | A workflow step invokes the harness. **Entry condition: corpus provenance** (§3) — CI reconstructs every input from version-controlled sources. |
| **2 — Measured floors gate the merge** | A gate script grades a committed baseline against a floors file and exits non-zero on breach; floors are measured with noise under them; the gate refuses to grade a partial snapshot; CI never writes the baseline back. | A floors file exists, and the gate is a **required status check** in branch protection. |
| **3 — The publish chain is provenance-pinned** | The graded snapshot carries a fingerprint of what produced it, and both the gate and the publisher refuse to act on a divergent one. Outward claims are generated or asserted from the published artifact. | A provenance sidecar exists and is read by two independent consumers. `SYS-019` tier 1 or 2 covers every outward number. |

Three notes the rungs do not carry on their own:

- **Tier 0 has a deceptive half-step.** `kb-agent` was the worked example on the day this amendment
  was drafted: it asserted its gold set's size and kind composition in `pytest` while never running
  retrieval — *set integrity gated, set execution not*. That is a genuinely useful check and it is
  worth having; it is also the kind of thing that reads as coverage in a checks list, and it does
  not reach tier 1, because nothing measures quality. (`kb-agent` cleared it the same day and now
  runs both eval arms; the `pytest` assertion stayed, which is the right outcome — the half-step is
  a *stopping place* to recognise, not a check to delete.)
- **Tier 2 is half a branch-protection setting.** A workflow cannot declare itself required. The
  classifier's own ADR-007 says this plainly, and a repo can sit at "tier 2 mechanism, tier 1
  effect" indefinitely without any file being wrong. When placing a repo, check the setting, not
  the workflow.
- **Tier 3 is not the goal for every repo.** It is the rung for repos that publish a number
  *outward*, which is the same population `SYS-020` uses to decide which repos earn tags. A repo
  whose numbers never leave it is finished at tier 2.

### Where the fleet actually sits (2026-08-02)

Read off the files, with citations. This table is a dated observation, not a guarantee — per
`SYS-019` it is tier 3 (a list), and it goes stale the ordinary way.

| Repo | Tier | Evidence | What is *not* gated |
|---|---|---|---|
| **defense-news-classifier** | **3** | Offline gate on push/PR runs `src/eval_gate.py` against floors in `evals/thresholds.toml`; partial-snapshot refusal in `_check_sample_size()`; provenance sidecar written by the producer and read by *both* `src/eval_gate.py` and `scripts/gen_metrics_artifact.py`; live lane restricted to `workflow_dispatch`/`schedule`; `evals/metrics.json` published and asserted by three downstream repos. | The required-status-check half of tier 2 is a branch-protection setting the workflow cannot declare. ADR-007 also volunteers that shared loose floors make the per-PR leg a **weak drift detector** — it trips on a large regression or a broken scorer, not on small real drift. |
| **kb-agent** | **1** *(as of 2026-08-02; was 0 when this amendment was drafted the same day)* | `ci.yml` shallow-clones `learning-notes`, builds the index against the clone via `KB_AGENT_NOTES_DIRS`, and runs **both** arms of `scripts/eval_retrieval.py` — unfiltered and `--kind-filter` — as reporting steps on every push and pull request ([`kb-agent/ADR-012`](https://github.com/sanlee-ys/kb-agent/blob/main/decisions/ADR-012-reconstruct-the-notes-corpus-in-ci.md)). §3's entry condition is met: a configured-but-absent notes dir now raises `FileNotFoundError` in `scripts/index.py` rather than skipping with a warning, so a short corpus fails the job instead of quietly scoring as bad retrieval. `tests/test_eval_retrieval.py` still asserts the gold set's size and kind composition. | The value, deliberately. There is no floors file, no gate script, and no required status check — a non-zero exit on either arm means the harness broke, not that retrieval regressed. Tier 2 is unstarted and correctly so: the first CI run (unfiltered recall@1 0.741 / recall@5 0.926 / MRR 0.813; `--kind-filter` recall@1 0.963 / MRR 0.981; 269 chunks over 44 files) is **one** measurement, and ADR-014's rule wants run-to-run noise under a floor. `scripts/eval_kind_usage.py` remains out of CI by design. |
| **faithfulness-judge** | **1** *(as of 2026-08-02; was 0 when this amendment was drafted the same day)* | `tests.yml` now runs the agreement eval after the existing `ruff` + `pytest` suite, still offline and keyless: it deletes `evals/results.md`, regenerates it with `uv run python src/score.py`, then fails on `git diff --exit-code -- evals/results.md` with a directed message ([`faithfulness-judge/ADR-003`](https://github.com/sanlee-ys/faithfulness-judge/blob/main/decisions/003-score-in-ci.md)). §3's entry condition was never in question here — `data/claims.yaml` and `data/judgments_*.yaml` are committed, so there was nothing to reconstruct. The `rm` is the liveness clause, and it is the reason this is not the theatrical version: `score.py` is a pure function over committed files, so a step that ran it without deleting the artifact first would diff git's checkout against git's checkout and pass vacuously if `score.py` ever stopped writing it at all. | The value, deliberately. There is no floors file, no gate script, and no required status check — this fails on **staleness** (the committed artifact disagrees with what the code produces), never on a number. κ is free to move; the file just has to move with it. **Tier 2 is blocked on something CI cannot fix**: an agreement statistic measured once has no noise band under it, and running CI more often does not supply one, because CI recomputes the same deterministic function over the same committed bytes and returns the identical figure every time. A second *sample* needs a paid judge re-run, which that repo's `CLAUDE.md` forbids doing to double-check. Also still ungated: the *claims* — `README.md` and `CLAUDE.md` restate figures from `evals/results.md` by hand. That is a `SYS-019` concern, explicitly out of scope of ADR-003, and it is now the larger of the two remaining holes. |
| **notes-api** | **n/a — no eval** | Gates contracts, not measurements: `scripts/gen_contract_schema.py --check` regenerates the provider-owned schema and fails if stale; `scripts/check_classify_contract.py` asserts the consumer half. | Nothing. This is the correct instrument for what this repo publishes; see the rollout note below. |
| **learning-notes** | **n/a — no eval** | Carries the closest adjacent mechanism in the system: `scripts/check_published_metrics.py` runs as its own CI job and asserts *another repo's* numbers as quoted here, failing on mismatch, on an unknown key, **and on zero markers**. Plus a generated-file drift job. | Nothing. |
| **architecture** *(this repo)* | **n/a — no eval** | Same adjacent shape one repo over: `scripts/check_program_metrics.py`, plus `scripts/lint_decision_log.py`, both with failure-path tests because running a guard against content it passes only exercises its happy path. | Nothing. |

The honest summary of that table: **one repo of six gates an eval, and no repo holds a harness that
CI never runs.** The unwired column is now empty. It held two repos when this amendment was drafted
— `kb-agent`, blocked by corpus reconstructibility, and `faithfulness-judge`, blocked by nothing at
all — and both cleared within the same day, the first by `kb-agent/ADR-012` and the second by
`faithfulness-judge/ADR-003`.

Note what the first clause does *not* say, and note that it has now survived two moves unchanged:
**the gated count is still one.** Both repos left the unwired column without entering the gated one,
which is exactly the distinction the ladder exists to keep visible — three of six repos now run an
eval, one of them blocks a merge on it. A number that runs on every PR and blocks nothing is a
report on a shorter timer, not a bar. The two tier-1 repos are also stuck there for *different*
reasons, which is worth keeping straight: `kb-agent` needs more CI runs, which time supplies;
`faithfulness-judge` needs a second sample that no amount of CI can produce.

### Rollout — who should move, and what it costs

Adopting this decision does not move anything. These are the work items adoption makes
*chippable*; each is its own repo-local ADR, per the original's `kb-agent` note.

**`kb-agent`: 0 → 1 — done 2026-08-02; 1 → 2 remains open.** The obvious candidate, because
`scripts/eval_retrieval.py` needs no API key and embeds locally — it is free and deterministic, so
gating it costs runner minutes and nothing else. The ordering is the original §3's, unchanged, and
the cost was almost entirely in the first step:

1. ~~Make the notes corpus reconstructible — an env override read by `scripts/index.py`, or a
   CI-written `projects.yaml`. This is the real work.~~ **Done** — `KB_AGENT_NOTES_DIRS`, an
   `os.pathsep`-separated override of `projects.yaml`'s `notes_dirs`. It came with a second change
   the plan did not name and should have: a configured-but-absent directory now **raises** instead
   of skipping with a warning, because the skip is the failure mode that makes a short corpus look
   like bad retrieval on a green job.
2. ~~Shallow-clone `learning-notes` in the job and point the index at it.~~ **Done**, on the
   predicted precedent, with no token. One thing the plan missed: the clone's *directory name* is
   load-bearing, since a note's `source` is `<dirname>/<file>.md` and the gold set spells them
   `learning-notes/…`.
3. ~~Build the index in the job.~~ **Done** — 269 chunks over 44 files, and the existing caches
   covered the model download as predicted.
4. ~~Run the harness with `--json` and commit the result as the baseline.~~ **Partly done, and the
   remaining part is deliberate.** Both arms run and report on every push and PR. No result is
   committed as a baseline, because one CI run is not a floor's worth of measurement — see below.
5. Only then: a gate script and a floors file. **Not started; this is the whole of the remaining
   1 → 2 move**, and it is a separate job.

**What floor values would the gate use? None that can be named today, and that is the finding.**
The retrieval figures `kb-agent` currently quotes in its README prose were measured on the
workstation, against a corpus assembled from an absolute local path that CI cannot reconstruct. A
number measured in one environment is not a floor in another — promoting it would be exactly the
"floor set low enough to accommodate the absence" this decision's Context warns about, wearing a
measured number's clothes. The closest existing recorded runs are the two arms of `kb-agent`'s
hybrid-versus-dense A/B (`kb-agent/ADR-010`), and they were measured in that same
un-reconstructible environment, so they are not eligible either. The runs that *would* be eligible
are the ones step 4 produces in CI — **plural**, because ADR-014's rule requires run-to-run noise
under the floor and one pass cannot supply it. Reconstruct → measure in CI, more than once →
set floors → gate.

*Updated 2026-08-02 — the first eligible run exists, and it is still one run.* CI now reports
unfiltered recall@1 0.741 / recall@5 0.926 / MRR 0.813 and `--kind-filter` recall@1 0.963 /
MRR 0.981. It reproduced a workstation run of the same recipe to three decimals, which is
reassuring about determinism and says **nothing** about run-to-run noise — a reproduction is not a
second sample. The finding above therefore stands unchanged: no floor can be named yet, and the
number to resist is 0.741, which now looks eligible in a way it was not last week precisely
*because* it was measured where the gate would run.

**`faithfulness-judge`: 0 → 1 — done 2026-08-02; 2 is a separate question, and the answer is not
"later," it is "blocked."** `src/score.py` is offline and deterministic over committed label files,
so recomputing agreement in CI costs one workflow step and no money — there was no
corpus-provenance blocker here at all, which is what made it the cheapest tier-1 move in the fleet,
and it landed as predicted ([`faithfulness-judge/ADR-003`](https://github.com/sanlee-ys/faithfulness-judge/blob/main/decisions/003-score-in-ci.md),
merged as [PR #18](https://github.com/sanlee-ys/faithfulness-judge/pull/18)). It cost two steps in
`tests.yml`, and the shape is worth recording because the cheap version would have been theater:
`score.py` is a pure function over committed files, so the step **deletes `evals/results.md` before
regenerating it** and then fails a `git diff --exit-code` on the artifact. Without the `rm`, the
check compares git's checkout to git's checkout and passes vacuously if `score.py` ever stops
writing the file. It fails on staleness, never on a value — no floors file, no gate script, no
required status check.

Tier 2 should **not** be assumed to follow, and this is now firmer than when it was written as a
caution. An agreement statistic measured once has no noise band under it, so the same refusal the
classifier applied to its scale run applies here. What the tier-1 work established is that CI
**cannot supply the missing sample**: it recomputes the same deterministic function over the same
committed bytes and returns the identical figure every run, so a reproduction is not a second
sample. A real one needs the judges re-run, which costs money and which that repo's `CLAUDE.md`
forbids doing to double-check. Contrast `kb-agent`, where the same "one run is not a noise band"
finding *is* dissolved by time, because each CI run there queries a freshly built index. Same rule,
two different kinds of block.

There is also a worthwhile move that is **not on this ladder and not done**: the README's restated
figures could be asserted against `evals/results.md` (`SYS-019` tier 1 or 2) today, which fixes a
claim-drift risk without touching CI's eval posture at all. ADR-003 scoped it out explicitly and by
name, as a different decision — `SYS-019` governs what may be claimed, this governs whether it is
enforced. It remains the larger of that repo's two open holes.

**`kb-agent`'s kind-usage eval is explicitly not part of this.** `scripts/eval_kind_usage.py`
spends one model call per gold query per run. Under the third corollary it belongs on an
owner-triggered lane or nowhere — never on a pull-request leg — and this decision recommends
nowhere for now.

**`notes-api` and `learning-notes` should not move.** Neither has an eval, and neither should
acquire one to satisfy a ladder. What they publish is contracts and quoted numbers, and both are
already gated by the right instrument (`SYS-018`, `SYS-019`). Inventing a measurement so a repo
can have a tier is the same error as an aspirational floor, one level up.

### Non-goals

- **Not a mandate to add API-spending CI legs.** The default for a paid eval is owner-triggered or
  absent. Nothing here authorises a scheduled spend in a second repo.
- **Not a framework, and not a shared gate package.** Each repo's gate stays its own script, for
  the reason `SYS-019` gives: a vendored guard that falls out of sync reports green from stale
  logic, which is worse than duplicating it. `SYS-019`'s fifth-checker revisit clause governs when
  that flips; this decision does not spend it.
- **Not a deadline.** Repos are placed on the ladder honestly, not required to climb by a date.
  Tier 0 is a legitimate resting place for a repo whose numbers do not leave it.
- **Does not supersede `SYS-019`; the two are orthogonal and both are needed.** `SYS-019` governs
  what may be *claimed* about a measurement; this governs whether the measurement is *enforced*. A
  number can be perfectly asserted against a published artifact and still be a report nobody
  re-checks — that is precisely the classifier's position before ADR-007, and precisely
  `faithfulness-judge`'s position now in reverse. Likewise `SYS-003` sets the eval-acceptance
  expectation for agent-callable tools; this says what "enforced" has to mean mechanically.
- **Does not authorise promoting an agentic lane to a gate.** `SYS-021` reserves that, and its
  reasoning stands: a silently-muted *gate* is a hole in the build. Every tier here is
  deterministic by construction.

### The successor is sequenced, and has not begun

The next item after this one is the **prompt-optimization loop** — the roadmap's standing
"next-after". It is **not started**, and the ordering is a constraint rather than a preference:
the loop's premise is that a prompt change can be scored automatically and accepted or rejected on
the result, which requires the repo it runs in to be at tier 2 or 3 already. Adopting this first
is what makes the loop's verdicts mean anything. One standard at a time.

### Downstream surfaces (adoption)

- **`README.md` decision-log table** — status cell moved to `Accepted`. Swept in the adopting PR;
  the lint fails if it drifts, so this one is enforced rather than listed.
- **`engineering/README.md`** — two lines described this decision as unratified: the keystone row
  ("system-wide pattern proposed in `SYS-017`") and the learning-sequence item ("settling
  `SYS-017`, which is still `Proposed`"). Both swept in the adopting PR. The keystone line's
  maturity marker is now accurate for the first time since the classifier pilot shipped.
- ~~**`program/README.md` — risk R6 and the `Next` entry.** Deliberately **not edited**. Both remain
  true after adoption: R6's remaining piece is still corpus provenance, and `Evals-as-CI for
  kb-agent` is still `Next` — this decision ratifies a standard, it does not wire a gate. What
  adoption gives R6 is vocabulary (it can now say `kb-agent` is at tier 0 and why), and that is a
  reason to revise the row when it is next touched, not a correction owed today. Recorded so a
  later reader can tell an untouched surface from an unswept one.~~ **Touched, and swept, later the
  same day** — `kb-agent/ADR-012` closed the corpus-provenance piece, so the deferral's own trigger
  fired within hours of being written. R6 now records provenance as done and names what is actually
  left (floors, a gate, a required check); the `Next` entry is narrowed to the 1 → 2 move rather
  than ticked, because `Evals-as-CI for kb-agent` is not finished at tier 1. `program/README.md` is
  the single edit point for both: the portal's roadmap page is **generated** from its
  Now/Next/Later section by `scripts/build_portal.py`, so there is no second surface to hand-edit.
- **`portal_src/telemetry.md`** — already repointed to this decision on 2026-07-18; the adoption
  changes nothing there.
- ~~**`kb-agent`, `faithfulness-judge`** — the rollout rows above. Each lands as a repo-local ADR
  citing this one, **after** adoption. Nothing in either repo is changed by this decision.~~ **Both
  landed 2026-08-02** — `kb-agent/ADR-012` and `faithfulness-judge/ADR-003`, each a repo-local ADR
  citing this one, in the predicted order and shape. The sentence still holds as written: neither
  repo was changed *by this decision*, which only made the work chippable.
- **`case-study/README.md`** — describes evals-as-CI in the narrative arc without a status claim,
  so it needs no edit. Checked, not assumed.
- **The fleet table itself** — a dated observation with a real staleness rate, by its own
  `SYS-019` classification. It is not enforced and should not be read as current once any of the
  six repos changes its CI. *The staleness rate turned out to be measured in hours, not months:*
  `kb-agent` changed its CI the same day, and the row was corrected by a human noticing, which is
  the failure mode the deferred generate-it-from-the-workflows option exists to remove. ~~One data
  point is not a trigger, but it is the first one.~~ **Two, now** — `faithfulness-judge`'s row went
  stale the same way and within the same day, and was likewise corrected by a human noticing rather
  than by anything failing. Two of six rows wrong inside 24 hours is a rate, not an anecdote. Still
  recording it rather than acting: the revisit clause this would spend belongs to `SYS-019`, and
  the honest read is that the table went stale *because* the ladder was doing its job and repos
  were moving — a burst during a rollout, not a steady state. Revisit if a row goes stale once the
  rollout is finished.

### Consequences of adopting

- **Makes easier:** answering "is this repo's number enforced?" with a rung instead of an
  argument, and scoping the next piece of work without re-deriving the ordering each time.
- **Costs:** the ladder is a vocabulary, and vocabularies invite tier-chasing. The non-goals exist
  to blunt that, and the two `n/a` rows are the load-bearing examples — a repo with no eval is not
  behind.
- **Forecloses:** wiring a gate before its corpus is reconstructible, and setting a floor from a
  number measured somewhere the gate will not run. Both were live options for `kb-agent` and both
  are now closed in writing.
- **A known hole, stated plainly:** nothing mechanically asserts the fleet table. There is no
  artifact publishing each repo's CI posture, so under `SYS-019`'s own tiers this is a list, with a
  list's failure rate. Generating it from the six repos' workflow files is a real option and is
  deliberately deferred — it would be the fifth checker, and `SYS-019`'s revisit clause should fire
  on a checker that needs *different* logic, which this one would.
- **Revisit when:** a second repo reaches tier 2, or when the prompt-optimization loop starts —
  whichever comes first. The second event is the one that will test whether the ladder's rungs were
  cut in the right places.
