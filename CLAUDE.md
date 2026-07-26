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

<!-- shared:links-verify v1 -->
## Links — verify before sending (hard rule)

Links given in chat must resolve: **full `github.com/<owner>/<repo>/blob/<ref>/<path>` URLs only**, **verify the path exists on the ref before sending** (unverified → say so), and **branch links are perishable** (prefer `main` once merged). Full rule + rationale: [claude-ops `conventions/links-verify.md`](https://github.com/sanlee-ys/claude-ops/blob/main/conventions/links-verify.md).
<!-- /shared:links-verify -->
