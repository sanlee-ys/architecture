# Telemetry / quality

!!! info "Placeholder — Phase 3"
    Nothing is deployed collecting metrics yet, so there are no live dashboards to embed
    (doing so now would be decoration over no data). This section turns real once a
    service runs somewhere — it tracks the OpenTelemetry item on the roadmap. See
    [SYS-008](decisions/SYS-008-documentation-portal.md).

What will live here:

- **Service health & traces** (OpenTelemetry) once `kb-agent` or `notes-api` is deployed.
- **Test coverage** — `notes-api` already produces `pytest-cov` (coverage.py) reports.
- **Eval / quality gates** — the classifier's eval harness; evals-as-CI (`SYS-007`, the keystone).
