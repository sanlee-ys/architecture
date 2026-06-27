# SYS-009: Security posture — the local-service trust model and house security rules

**Status:** Accepted
**Date:** 2026-06-26
**Deciders:** San Lee

---

## Context

The first house-wide security audit was run across every repo in the system
(`defense-news-classifier`, `kb-agent`, `notes-api`, `dotfiles`, `architecture`,
`learning-notes`, plus the `sanlee-ys` profile). The headline: **no Critical and no High
findings** — no committed secrets or private keys anywhere, no injection sinks
(`eval`/`exec`/`pickle`/unsafe-YAML/SQL), no vulnerable dependency pins. What it *did* surface
were Medium-and-below items that all trace back to one unwritten assumption: **these are
personal, single-user, local services, several of them wired together with LLM and HTTP
seams.** That assumption was never written down, so its security consequences were implicit —
and an implicit assumption isn't a control.

This ADR writes the posture down once, so (a) a non-security-expert can reason about "is this
okay?" by checking the trust model rather than re-deriving it, and (b) future changes don't
silently regress it. It is the canonical place this system records *what is trusted, what is
not, and the rules that follow.*

### What the audit found (baseline, 2026-06-26)

| Repo | Risk | What was done |
|------|------|---------------|
| `notes-api` | Medium | Bind to loopback by default; no web-console exposure (SQLite has no built-in web UI, unlike the H2 console that was present in the Java/Spring Boot version); error-leak hygiene; trust boundary documented in its `ADR-002`. No auth added by design (see rule 1). |
| `kb-agent` | Low–Med | Prompt-injection rule added to the agent system prompt; SSRF guard validates `projects.yaml` endpoints (http/https + loopback allowlist) before any call. |
| `defense-news-classifier` | Low | `/classify` 502s no longer echo the raw upstream exception to callers (logged server-side instead). Already strong: non-root Docker, no secrets, pinned deps, output re-validated. |
| `dotfiles` | Low | `.gitignore` now blocks plain `*.bak` (not just `*.bak.*`); README prefers the reviewed clone path over paste-into-shell. Key guardrails already effective. |
| `architecture` | Clean | Docs/portal only; mermaid `securityLevel:'loose'` is safe because diagram source is first-party. |
| `learning-notes` | Low | Static-site build; HTML/link escaping and CDN-SRI only matter if externally-authored notes are ever accepted. |
| `sanlee-ys` | Clean | Profile README + images; no code surface. |

## Decision

### The trust model

- **Trusted:** code in these repos, and local configuration the author controls
  (`projects.yaml`, `.env`, properties files). Local config is a trust boundary — whoever can
  edit it is already trusted.
- **Untrusted (treat as data, never as instructions or as a safe target):**
  - Third-party content that reaches an LLM — dependency READMEs, generated KB stubs,
    free-form notes, and article text submitted for classification.
  - Anything arriving over the network, and any URL/endpoint a request might be sent to.
- **Severity is deployment-driven.** For a single-user tool reachable only over loopback,
  "no authentication" is an *accepted* risk behind a documented boundary. The **same code
  becomes High-severity the moment it is exposed beyond localhost** — so exposure, not the
  code, is the thing that's gated.

### House security rules (apply to every repo)

1. **Local services bind to loopback by default; networking one requires auth first.** A
   personal service listens on `127.0.0.1` unless deliberately and securely deployed. Adding a
   second client or any non-local reachability is the trigger to add real authentication —
   not something to bolt on after exposure. (Instance: `notes-api/ADR-002`.)
2. **LLM inputs from third-party/free-form sources are DATA, not instructions.** Any agent or
   prompt that ingests READMEs, notes, retrieved chunks, or user-submitted text must be told
   explicitly not to follow instructions embedded in that content. (Instance: `kb-agent`
   system prompt.)
3. **Validate cross-service endpoints before calling them.** HTTP seams whose target comes
   from config must check scheme (`http`/`https`) and host (loopback by default, widenable via
   an env allowlist) before issuing a request, so a poisoned config can't redirect a request —
   which may carry user content — at an arbitrary host. (Instance: `kb-agent` SSRF guard.)
4. **Never return internal/upstream error text to callers.** Log the real cause server-side;
   return a generic message/status. Don't leak stack traces, exception messages, model names,
   or request fragments. (Instances: classifier `/classify`; notes-api error settings.)
5. **Secrets live in environment variables, never in the repo.** Keys are read from env; only
   `.example` files with placeholders are committed. `.gitignore` actively blocks key material
   (`id_*` except `*.pub`, `*.pem`, `*.key`) and config backups (`*.bak*`).
6. **Bootstrap scripts: prefer a reviewed clone over paste-into-shell**, and only use upstream's
   blessed install path for third-party installers (e.g. Homebrew's `curl | bash` is accepted
   as upstream's official method; don't invent unverified equivalents).

## Consequences

- **A non-expert can now answer "is this safe?"** by checking the rule and the trust model,
  instead of re-reasoning from scratch. Each fix points back here; this ADR points to each
  instance.
- **Safe-by-default running.** Loopback binding and endpoint validation mean simply *running*
  the services doesn't expose them — the dangerous state requires a deliberate action.
- **The accepted risk is explicit.** "No auth on notes-api" is a written, owned decision tied
  to the loopback boundary — not a silent gap. The cost is real: bypass the boundary
  (`SERVER_ADDRESS=0.0.0.0` without auth) and the service is open. That tradeoff is now visible.
- **An audit obligation.** This posture is only honest if re-checked. See the triggers below.

### When to revisit

Re-open this ADR (and record a superseding `SYS-NNN`) when **any** fire:

1. **A service needs to be reachable beyond the local machine, or gains a second/multi-user
   client.** → add real authentication (e.g. a shared API-key filter across the relevant
   seams) before exposing it; for multi-user, add per-resource ownership.
2. **A new external input reaches an LLM or a new cross-service seam is added.** → apply rules
   2–4 to it explicitly and note the instance here.
3. **A dependency advisory lands** for a pinned package, or a new repo joins the system. →
   re-run the audit; refresh the baseline table.
4. **Any finding is ever rated High/Critical.** → fix before merge, don't defer.

> Operational note to future-me / assistant: when a session adds a network listener, a new LLM
> input, or a new HTTP seam, surface this ADR and walk the relevant rule — the point of writing
> them down is so the check doesn't depend on memory.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Add authentication everywhere now | Real cost (new shared secrets across repos + coordinated client changes) to protect single-user tools that shouldn't be networked; over-engineering. Gated on the exposure trigger instead. |
| Leave the posture implicit ("it's all local anyway") | The audit showed the assumption was undocumented and some defaults (e.g. all-interfaces binding) contradicted it. An unwritten assumption isn't a control. |
| Per-repo security notes only, no house doc | No single place to reason about cross-cutting rules or the shared trust model; each LLM/HTTP seam would re-decide the same questions. Per-repo ADRs still exist for local specifics, linked from here. |
| Treat severity as fixed per finding | Misleading: "no auth" is acceptable on loopback and severe when exposed. Tying severity to deployment context is what makes the accepted risks honest. |
