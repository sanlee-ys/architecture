# CLAUDE.md

Guidance for AI agents working in this repo.

## What this is

The system-level registry: decisions that span more than one repo, recorded as numbered
**`SYS-NNN`** records under [`decisions/`](decisions/) (`SYS-001` sets the format). A
decision affecting only one repo belongs in that repo's own `decisions/`, not here.

## `portal/` is generated — edit the source, not the output

The browsable portal is assembled from the source repos by
[`scripts/build_portal.py`](scripts/build_portal.py); `mkdocs.yml` carries the run
instructions. Hand-edits under `portal/` are overwritten on the next build, silently.
Edit the real source in the owning repo — or `portal_src/` for portal-only chrome —
then re-run the script.

## The guard scripts have tests — run them when you touch one

`scripts/check_program_metrics.py` and `scripts/lint_decision_log.py` are also *run* by CI
against this repo's real content, which only ever exercises their happy path. The failure
paths — the drift detection that is the point of both — are covered by [`tests/`](tests/)
instead, against stubbed input, with no network access.

```bash
uv run --with pytest pytest tests/ -q
```

These tests pin **current** behaviour; they are not a spec to design against. If you change
what a guard detects, change its test in the same commit and say why in the docstring. If
you add a check without a failure-path test, the guard can stop guarding and CI stays
green — which is the failure both scripts exist to prevent, one level up.

<!-- shared:links-verify v1 -->
## Links — verify before sending (hard rule)

Links given in chat must resolve: **full `github.com/<owner>/<repo>/blob/<ref>/<path>` URLs only**, **verify the path exists on the ref before sending** (unverified → say so), and **branch links are perishable** (prefer `main` once merged). Full rule + rationale: [agent-ops `conventions/links-verify.md`](https://github.com/sanlee-ys/agent-ops/blob/main/conventions/links-verify.md).
<!-- /shared:links-verify -->
