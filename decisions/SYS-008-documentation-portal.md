# SYS-008: A generated documentation portal — one browsable view over the whole system

**Status:** Accepted
**Date:** 2026-06-23
**Deciders:** San Lee

---

## Context

The system now spans six repos — `architecture` (this one: the cross-cutting hub for product,
program, engineering, case-study, and the `SYS-*` log), plus `kb-agent`, `notes-api`,
`defense-news-classifier`, `learning-notes`, and the built `learning-notes-site`. Every fact
already lives in its right contract: per-repo `decisions/`, `docs/`, and READMEs for repo-scoped
material; this repo's `SYS-*` log and `program/` / `engineering/` / `case-study/` for the
cross-cutting layer (`SYS-001`).

What's missing is not more documentation — it's a **single place to read it.** Today,
understanding the system means opening six repos and stitching them together in your head. A prior
SWE team had the opposite: one portal where application docs, diagrams, and SRE/telemetry sat
together and you could just *browse* in downtime. That pattern has a name — an **internal
developer portal** (the open-source reference is Backstage).

And reading is only half of it: the sharpest friction is **switching modes on a whim** — flipping
from an ADR to the code it governs, or back, currently means closing one repo and opening another.
The portal has to put *decisions and source one click apart*, not merely collect docs in one tab.

Two forces make this worth an ADR now rather than an ad-hoc page:

**1. "One system" is asserted but not yet legible.** `SYS-003` connected the repos with a
tool-layer contract and `SYS-007` framed engineering as the substrate under the P-tracks — but a
reviewer (or future-me) still can't *see* the system in one place. The portal is the artifact that
makes the 4→1 claim browsable instead of narrated.

**2. The mechanism already exists, scoped to one repo.** `learning-notes` already runs
docs-as-code — a `mkdocs.yml`, a published static site, and a D3 `concept-map.html`. The
capability is proven; it has simply never been pointed at the whole system. The gap is an
**aggregation layer**, not a new tool.

The relevant risks from the program register apply directly — **R3 (breadth creep)** and **R4
(planning theater)**: a portal is documentation-of-documentation, the kind of polishing that can
quietly preempt the actual keystone work (`SYS-003` evals-as-CI; the `notes-api`
classify-and-writeback loop).
The decision below is scoped to stay cheap and aggregation-only for exactly that reason.

## Decision

Build a **generated, read-only documentation portal** hosted in this `architecture` repo and
published to GitHub Pages, as the single browsable view over the system.

**The governing principle — aggregate, never duplicate.** Each fact keeps one source of truth in
the repo that owns it. The portal is a *generated view* over those sources, never a hand-maintained
second copy. (This is the docs analogue of the working rule that aggregated artifacts get wired by
a single integrator, once, after the content lands.)

Concretely:

- **Host & tool:** MkDocs Material in `architecture/`, published to GitHub Pages — the same stack
  already proven in `learning-notes`, not a new dependency. The generated docs tree is assembled by
  `scripts/build_portal.py`; nothing under the build dir is authored by hand.
- **The front door is an interactive system map.** Landing on the portal shows a browsable map of
  the whole system — the repos, the `SYS-003` tool seams between them, and the event flow —
  extending the existing `learning-notes` D3 concept-map technique up to system scale. Until that
  map lands (Phase 2) the home page is a launchpad of the same links.
- **Code is always one click away.** Every app and decision page carries a prominent deep link to
  its source on GitHub, so flipping from an ADR to the code it governs — or back — never means
  hunting across repos. Browsing source stays *on GitHub* (its code browser, search, and blame beat
  any static mirror); the portal is the reading-and-navigation layer, not a second code copy.
- **Aggregation by CI sync.** A GitHub Action in this repo checks out each project repo, copies its
  `docs/` + `decisions/` + `README` into the MkDocs tree under a per-app section, builds, and
  deploys. The repos stay fully independent (preserving the one-concern-per-repo working model);
  only the *wiring* centralizes here. The same assembly script runs locally against the sibling
  repos, so the portal is browsable on disk before any deploy.
- **Sections:** System overview (the map) · Decisions (every `SYS-*` and repo `ADR-*` in one wall)
  · Apps (one section per repo, each with its code link) · Diagrams (Mermaid, rendered natively by
  MkDocs Material).
- **Telemetry is deferred to a placeholder.** A "Telemetry / quality" section exists but is
  explicitly empty for v1 — nothing is deployed collecting metrics yet, so embedding live
  dashboards would be fiction. It becomes real in a later ADR once a service runs somewhere (it
  rhymes with the OTel item already on the roadmap — `SYS-007` / R7).
- **Not Backstage.** Explicitly right-sized: a static aggregator, not a deployed app, for a
  one-person six-repo system.

## Consequences

- **The 4→1 system finally becomes legible in one place** — the artifact `SYS-003` / `SYS-007`
  implied but never produced. Browsable in downtime, and decisions sit one click from code, which
  was the actual ask.
- **It doubles as a portfolio asset.** A reviewer browsing one clean system map + decision wall is
  the single-person-three-hats narrative (`SYS-007`) made tangible — stronger than describing six
  repos out loud.
- **Sources stay authoritative; the portal can't rot independently.** Because it's generated, drift
  is impossible by construction — a stale portal means a stale source, which is the right place to
  fix it.
- **It costs roadmap attention, and that is the real risk (R3 / R4).** A portal is not on the
  critical path of either keystone (evals-as-CI; the `notes-api` consumer). Mitigated three ways:
  v1 is *aggregation of existing content* (little new writing), the build is phased so a thin
  version ships first, and telemetry — the most infra-heavy pillar — is cut from v1.
- **The interactive map is the one piece of genuinely new, custom code to own.** Accepted
  deliberately because it's the highest-leverage part of the experience and reuses a proven
  technique — kept honest by building it on a working aggregation skeleton rather than first.
- **One new CI surface** (the sync Action) to keep green — modest, and centralized in one repo by
  design.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **Backstage / a real IDP** | Built for orgs with many services and teams; it's a deployed app that becomes its own maintenance project. Absurd overhead for one person and six repos. |
| **Hand-maintained central wiki** (Notion / Confluence / a docs repo with copied content) | Violates aggregate-don't-duplicate; goes stale the day after writing because the copy drifts from the source. The exact anti-pattern this ADR exists to avoid. |
| **Mirror source code into the portal** | A static code mirror is strictly worse than GitHub's browser (no search, blame, or history) and balloons the build. The portal deep-links to code instead of copying it. |
| **Monorepo-ify the docs** (or all repos) | Breaks the deliberate one-concern-per-repo / parallel-session working model and the per-repo `decisions/` locality `SYS-001` protects. Too big a structural change for a reading convenience. |
| **Git submodules instead of CI sync** | Simpler to bootstrap, but submodule-pinning is clunky to keep current and easy to forget; CI sync always builds from each repo's latest `main` with no manual pointer bumps. Noted as the fallback if the Action proves heavy. |
| **A standard docs landing page instead of the map** | A plain nav sidebar ships faster, but the map is the part that actually makes "one system" *feel* like one system — the whole reason the portal beats just reading six READMEs. |
| **Build telemetry into v1** | Nothing is deployed emitting metrics; live panels would be decoration over no data. Deferred until a service actually runs (ties to the roadmap OTel item). |
