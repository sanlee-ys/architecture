# SYS-015: Publish the Claude operating layer as a public repo (claude-ops)

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** San Lee

---

## Context

Running Claude Code as an engineering teammate grew into a real subsystem of
its own: incident postmortems (four credential exposures in one week, and the
mechanical guard that ended them), a layered security posture, custom skills,
and a written operating model (DCB — Direction / Contracts / Bar). That work
was authored inside a private strategy repo, which can't serve its two real
audiences — anyone running an agentic CLI with credentials on their machine,
and the portfolio, where security posture for AI tooling should be inspectable
like any other engineering work.

The split was executed on 2026-07-05 as the public repo
[`claude-ops`](https://github.com/sanlee-ys/claude-ops). Its repo-local
[ADR-001](https://github.com/sanlee-ys/claude-ops/blob/main/decisions/ADR-001-public-claude-ops-repo.md)
carries the full decision — the four pillars, the publication boundaries, and
the canonicality/sync model — and explicitly deferred this SYS entry as a
follow-up per the two-tier convention (`SYS-001`): the decision *crosses
repos* (a private repo remains the system of record; a public repo carries
the curated copies), so the system log must record it.

## Decision

Record the split at the system tier, deferring to claude-ops
[ADR-001](https://github.com/sanlee-ys/claude-ops/blob/main/decisions/ADR-001-public-claude-ops-repo.md)
as the authoritative statement of scope. The load-bearing points, restated:

- **`claude-ops` is the curated publication, not the system of record.** The
  private working copies keep the un-redacted detail; new material (incidents
  especially) is written privately first and published only after
  de-identification.
- **The boundaries live in ADR-001** — no credential values ever, no private
  repo names or contents, employer internals capped at the public-résumé
  ceiling, no raw permission allowlist. Changes to those boundaries are made
  *there*, not here.
- **The portal lists `claude-ops` link-only.** It gets a row in the launchpad's
  "Repos at a glance" table (like `learning-notes`) but is **not** aggregated
  into the portal the way the app repos are: it isn't part of the running
  system the portal documents, it has a different audience, and it's built to
  stand alone.

## Consequences

- **What this makes easier.** The operating-layer work (security incidents,
  the guard, the skills, DCB) is now portfolio-visible and citable; the system
  decision log has no dangling reference to a repo it doesn't acknowledge.
- **What it costs.** Dual-sourcing invites drift between private canon and
  public copy — accepted in ADR-001 because the alternative (public-canonical)
  forces redaction at write time, which is where redaction mistakes happen.
  A fifth public repo also joins the maintenance surface (branch hygiene,
  link checks).
- **What it forecloses / defers.** The portal stays a view over the *projects
  system*; if `claude-ops` ever grows portal-worthy docs, aggregating it is a
  new decision, not an implied extension of this one.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **Keep the operating layer private** | Fails both audiences: the failure modes documented (env-var echo, config reads, interpreter bypasses) match known upstream issues and are useful precisely to people who can't read a private repo; and invisible engineering work does nothing for the portfolio. |
| **Publish it inside this `architecture` repo** | Scope mismatch: this repo governs the projects system (apps, contracts, portal). The Claude operating layer spans *all* work on the machine, not just these projects, and its incident/security content has its own audience and cadence. |
| **Make the public copy canonical** | Rejected in claude-ops ADR-001: every private detail would pass through a redaction step at write time — exactly where redaction mistakes happen. Private-canonical + curated sync keeps the failure mode away from the sensitive material. |
| **Aggregate claude-ops fully into the portal** | Audience mismatch — the portal reads as the projects system's documentation; claude-ops is a self-contained publication with its own README and structure. A link-only row gives discoverability without conflating the two. |
