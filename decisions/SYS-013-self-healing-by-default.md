# SYS-013: Design services to self-heal — detect and recover before a human has to

**Status:** Accepted
**Date:** 2026-07-03
**Deciders:** San Lee

---

## Context

`SYS-012` fixed a concrete instance of a recurring pattern: `portfolio` and
`learning-notes` both hit the same GitHub Pages deploy flake repeatedly, and
one failure sat silently unresolved for ~7 hours until an unrelated push
happened to retry it. The fix (Actions-based deploy + a `pages` concurrency
group) was reactive — something broke, it got noticed via email, then
patched. The same day, a second reactive fix landed: a third-party tool's
missing Windows no-window flag, caught only because its symptom (flashing
console windows) was visible enough to ask about.

Both fixes were correct, but both depended on a human noticing first. The
question this ADR answers: should the next round of design work bake
failure-recovery in from the start, instead of waiting for the next
incident to surface it?

## Decision

Default to **self-healing** as a design axis for services in this system —
alongside correctness, cost, and latency, not subordinate to them. Concretely,
new infra/tooling work should ask "how does this recover without a human"
before shipping, not after the first incident:

- **Retries with backoff** on operations known to have transient failure
  modes (external API calls, deploys, anything already observed to flake —
  `SYS-012`'s concurrency group is the first instance of this).
- **Idempotent operations** wherever a step might need to re-run — a retry
  or a self-heal attempt must be safe to repeat, not just fast to repeat.
- **Concurrency/serialization guards** where parallel triggers can race
  each other into a broken state (again, `SYS-012`).
- **Self-triggered remediation** where a known-bad state has a known-good
  fix — e.g. a health check that restarts a stuck component itself, rather
  than paging a human to run the same restart command every time.

**Every self-healing mechanism must ship with a visibility signal.**
Auto-recovery that succeeds silently every time is fine; auto-recovery that
fires *repeatedly* for the same underlying fault is a masked incident, not
a solved one. Concretely: if something self-heals more than once in a
short window, that needs to surface somewhere (a log line grep-able later,
a counter, a flagged review item) — not just heal again quietly. This is
the same principle `SYS-012`'s own writeup leaned on: it disclosed that the
first Actions-based deploy also failed once and needed a retry, rather than
presenting the fix as a clean 100% guarantee.

## Consequences

- Fewer incidents require San to notice a symptom, diagnose it, and hand-patch
  it in a follow-up session — the `SYS-012` loop (email → investigate → fix)
  is the failure mode this is meant to reduce.
- Added complexity per service: every retry/backoff/guard is more code and
  more failure modes of its own (a retry loop can itself loop forever without
  a cap; a circuit breaker needs its own reset condition). Each addition
  should be scoped to a failure mode that's actually been observed or is
  clearly foreseeable, not spec'd in speculatively everywhere.
- Risk of masking: self-healing that isn't paired with a visibility signal
  (per the Decision above) can make a persistent problem *look* solved while
  it keeps quietly recurring. The pairing requirement is the guard against
  that, and should be treated as non-optional, not a nice-to-have.
- This is a standing lens for design and code review, not a one-time project.
  There's no single "done" state — it's applied per-decision as new services
  and infra get built.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **Keep handling failures reactively as they surface** | The status quo going into this ADR — it works, but only as fast as someone notices. `SYS-012`'s 7-hour silent-stale-deploy case shows the cost of relying on that alone. |
| **Invest in monitoring/alerting instead of auto-recovery** | Solves detection, not toil — a human still has to act on every alert. Worth pairing with self-healing (per the visibility requirement above), not a substitute for it. |
| **A third-party uptime/status-check service for public sites** | Would catch public-facing outages (e.g. `sanlee.me` down) but not CI/tooling-level flakes like the Pages deploy race or the graphify console-flash bug — the failures actually hit this week were both internal to the dev workflow, not customer-facing downtime. |
