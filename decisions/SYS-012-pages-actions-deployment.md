# SYS-012: GitHub Pages — deploy via Actions, not the legacy branch build

**Status:** Accepted
**Date:** 2026-07-03
**Deciders:** San Lee

---

## Context

Both public static sites — `portfolio` (sanlee.me) and `learning-notes`
(sanlee-ys.github.io/learning-notes) — were serving GitHub Pages via the
**legacy** build path: Pages configured to "deploy from a branch," with
GitHub building and publishing automatically behind the scenes whenever
`main` moved. Neither repo had a deploy step of its own; `pages build and
deployment` showed up as a run GitHub injects, not a workflow file either
repo owns.

That pipeline failed intermittently with `Deployment failed, try again
later` — three times on `portfolio` in two days (2026-07-02 16:35,
2026-07-03 01:40, 2026-07-03 15:23) and twice on `learning-notes` on
2026-07-02 (16:01, 16:22). The failure isn't tied to anything in either
repo's content or CI — `portfolio`'s only workflow (`qa.yml`) was green
every time. It's the legacy pipeline itself.

Worse than the failure rate: it doesn't reliably self-heal on its own timeline.
One `portfolio` failure (07-02 16:35) sat broken until the next unrelated push
happened to trigger a fresh build — roughly 7 hours later. A merged fix or
content change can silently not go live for hours, with no signal anywhere
in either repo — the only place it surfaces is GitHub's own email
notification, which nothing in the Claude session tooling sees or polls.

## Decision

Migrate both sites' Pages source from "deploy from a branch" (`build_type:
legacy`) to **Actions-based deployment** (`build_type: workflow`):

- Each repo gets its own `.github/workflows/deploy-pages.yml`:
  `actions/checkout` → `actions/configure-pages` →
  `actions/upload-pages-artifact` (`path: "."`, whole repo root — both sites
  are no-build static HTML) → `actions/deploy-pages`.
- `concurrency: { group: pages, cancel-in-progress: false }` on the deploy
  job. This is GitHub's documented mitigation for the failure mode above —
  the legacy pipeline has no equivalent serialization, which is the likely
  source of the "try again later" conflict.
- Pages source flipped per-repo via `gh api --method PUT repos/{owner}/{repo}/pages
  -f build_type=workflow` (no UI click needed).
- `architecture`'s portal (`SYS-008`) was already on `build_type: workflow`
  from the start and has a 100% success rate across its last 10 deploys —
  this decision brings the other two public sites in line with that existing,
  working pattern rather than inventing a new one.

## Consequences

- Deploys are now deterministic: every push to `main` runs an
  Actions workflow this repo owns and can inspect (`gh run list`,
  `gh run view --log-failed`), instead of an opaque GitHub-managed build.
- A stuck deploy is now visible from inside the repo (a red run in Actions)
  rather than only via an email neither the repo nor any session tooling
  reads.
- Not a full guarantee: right after flipping `learning-notes`'s
  `build_type`, the very first Actions-based deploy also hit
  `Deployment failed, try again later` once, then succeeded on immediate
  retry. So the underlying error is a genuine transient condition on
  GitHub's deployment API, not purely a legacy-pipeline artifact — the
  concurrency group prevents *self-inflicted* races from adding to it, but
  an isolated retry may still occasionally be needed.
- No content or CSS changed on either site — this is a CI/deploy-path
  change only.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **Do nothing, treat it as a known GitHub flake** | Already recurred 5 times across two repos in two days, and the 7-hour stuck-deploy case shows it doesn't reliably self-heal — the cost of ignoring it is a site that's silently stale with no in-repo signal. |
| **Add a retry loop around the legacy deploy (e.g. a workflow that polls Pages status and re-triggers)** | Would be working around a pipeline neither repo controls, with no workflow file to attach the retry logic to in the first place. Migrating to the Actions path replaces the flaky mechanism instead of papering over it. |
| **Build a custom notifier (webhook/cron) so failures surface without email** | Solves visibility, not the underlying failure rate. Worth revisiting only if Actions-based deploys still fail with meaningful frequency after this change. |
