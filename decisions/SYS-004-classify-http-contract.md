# SYS-004: Freeze the /classify HTTP contract between the classifier and kb-agent

**Status:** Accepted
**Date:** 2026-06-22
**Deciders:** San Lee

---

## Context

`kb-agent`'s `classify_snippet` tool reaches across a repo boundary: it POSTs to the
`defense-news-classifier` service's `/classify` endpoint over HTTP (base URL read from
`projects.yaml`, never hardcoded). This is the system's first live cross-service seam —
the agent *drives* a tracked project rather than describing it — and it is the seam the
[program risk register](../program/README.md#risk-register) flagged as **"silent contract
drift"** (R6's cousin): the classifier (provider) and `kb-agent` (consumer) are separate
repos with separate release cycles, so the provider can rename a field or change an enum
and nothing fails until the agent silently mis-reads a response at runtime.

[SYS-003](SYS-003-agent-tool-layer-contract.md) already governs the **agent-facing**
side of this tool: the *observation envelope* (`status` / `summary` / `payload` /
`source` / `next_actions`) that `classify_snippet` returns to the model. But SYS-003
deliberately treats wire format as "an implementation detail" — it says nothing about
what the bytes on the `/classify` HTTP call look like. That underneath layer — the
request body, the success body, the error codes — has so far been defined only by the
two implementations happening to agree. That agreement is currently correct (verified
below) but unprotected: it is asserted by code on each side, not pinned as a contract
either side is obligated to honor.

This ADR freezes that wire contract and ties a versioning rule to it, so a breaking
change to the provider can no longer land without a coordinated consumer update.

**Source of truth (the contract is read *from* the code, not invented here):**

- Provider shape — classifier `src/api.py`: `ClassifyRequest` (the request model) and
  `ClassifyResponse` (the two-field response model), plus the `/classify` handler's
  422/502 behavior.
- Enums — classifier `src/classify.py`: `CATEGORIES` and `DOMAINS`.
- Consumer — `kb-agent` `agent/tools.py`: `classify_snippet`, which builds
  `{"text": ...}`, calls `POST {base}/classify`, and reads `category` /
  `operational_domain` out of the 200 body.

## Decision

Adopt the following as the **frozen `/classify` contract**. Both repos are bound to it;
neither may change it unilaterally (see *Versioning rule*).

**Endpoint.** `POST {base}/classify`, where `{base}` is the classifier service's base
URL, supplied to `kb-agent` via the `defense-news-classifier` entry in `projects.yaml`
(config, not code).

**Request body (JSON).**

```json
{ "text": "<string>" }
```

- `text` is required, **1–10 000 characters**.
- Empty or whitespace-only `text` is invalid → **422** (the service strips and
  re-checks, so a blank string that slips past `min_length` is still rejected).

**Success response — HTTP 200 (JSON).**

```json
{ "category": "<string>", "operational_domain": "<string>" }
```

- **Exactly these two fields** — no more, no fewer. This is the load-bearing clause.
- `category` ∈ `{ procurement, operations, policy, technology, industry }`.
- `operational_domain` ∈ `{ air, land, sea, cyber, space, multi }`.

**Error responses.**

| Status | Body | Meaning |
|--------|------|---------|
| **422** | `{ "detail": ... }` | Invalid input — blank/whitespace-only or over the 10 000-char cap. |
| **502** | `{ "detail": ... }` | Upstream LLM call failed (network, rate limit, API error). The fault is the dependency, not the request — so it is a 502, not a 500, and a retry is reasonable. |

**Versioning rule (the point of freezing it).**
Adding, removing, or renaming a response field, or changing either enum's membership,
is a **breaking change to this contract**. Per the classifier's semver policy it requires
**all** of:

1. a **MAJOR** semver bump on `defense-news-classifier` (e.g. the planned `v3.0.0`);
2. a **coordinated `kb-agent` update** — landed together with the provider change, not
   after it drifts — so the consumer reads the new shape; and
3. an **update to this ADR** (a new row in the table below, or a superseding `SYS-NNN`).

The concrete worked example is the classifier's roadmapped **`v3.0.0` `region` field**:
the response becomes `{category, operational_domain, region}`, which adds a field and
therefore breaks this contract. It is exactly the change this rule exists to gate — it
may not ship as a minor or a patch, and it may not ship on the provider alone.

Non-breaking changes — adding a *new* endpoint, loosening the char cap, improving an
error `detail` string — keep the contract intact and need only the ordinary minor/patch
treatment.

**Both sides now carry contract tests pinning this shape**, so a drift is caught by a
red build, not by a mis-classified answer in production:

- **Provider (`defense-news-classifier`):** a test pins `ClassifyResponse`'s fields and
  the `category`/`operational_domain` **enums** to `CATEGORIES`/`DOMAINS`, and the API
  tests assert the 200 body is exactly those two fields and that bad input → 422 /
  upstream failure → 502. Renaming a field or editing an enum turns the suite red.
- **Consumer (`kb-agent`):** a test asserts `classify_snippet` parses this 200 shape into
  its SYS-003 `payload` (`{category, operational_domain}`), and the tool is required to
  **degrade gracefully on a malformed response** — a body missing a field returns a
  SYS-003 *error observation* with recovery guidance, never an unhandled exception that
  crashes the tool-use loop.

Both repos run these in CI (as do all three code repos now — `defense-news-classifier`,
`kb-agent`, and `notes-api`), so the contract is enforced on every push, not by memory.

**Relationship to SYS-003 (two layers, not a duplicate).**

- **SYS-003** governs the *agent-facing observation envelope*: how `classify_snippet`
  reports success/failure **to the model** (`status` + `payload` + `source`, or
  `next_actions` on failure).
- **SYS-004** governs the *cross-service HTTP wire contract* **underneath** that tool:
  the request body, the two-field 200 response, and the 422/502 error codes the
  classifier service and `kb-agent` exchange over the network.

`classify_snippet` is where the two meet — it translates a SYS-004 HTTP response into a
SYS-003 observation. A provider change that honors SYS-004 (same two fields, same enums)
is invisible to SYS-003; a provider change that breaks SYS-004 is precisely what the
versioning rule above forces into the open.

## Consequences

- **Drift is now loud, not silent.** The exact failure the risk register named — the
  provider changing the wire shape and the agent mis-reading it at runtime — is caught by
  a red build on whichever side falls out of sync, before it ships.
- **The `region` change has a defined, gated path.** `v3.0.0` can't sneak in as a minor:
  the rule names it as the worked breaking example, and lists the three things that must
  move together (classifier MAJOR + coordinated `kb-agent` update + this ADR).
- **The two repos stay decoupled, deliberately.** The seam is still HTTP and
  config-driven, not a shared import or package — each keeps its own environment and
  release cycle. The contract is the coupling; the code is not.
- **It costs coordination on breaking changes.** A response-shape change can no longer be
  a one-repo edit — that friction is the *point* (it's what makes the consumer safe), but
  it is a real tax on the provider, paid now while there is exactly one consumer.
- **The contract must be kept in step with the code.** If `src/api.py` or the enums in
  `src/classify.py` change, this ADR is stale until updated — the same revisit obligation
  SYS-002 and SYS-003 carry. The contract tests are the tripwire that this happened.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Leave the wire shape implicit, defined only by the two implementations (status quo) | Exactly the "silent contract drift" risk: the provider can rename a field or change an enum and nothing fails until the agent mis-reads a live response — the failure mode this ADR exists to close |
| Fold the wire contract into SYS-003 | SYS-003 is intentionally transport-agnostic ("format is an implementation detail; the fields are the contract"). The HTTP request/response/error shape is a *different* contract at a *different* layer; conflating them would muddy both |
| Version the response with an explicit `version` field or `Accept` header negotiation | Over-engineered for one provider and one consumer in one person's system; semver on the service + a coordinated consumer update + this ADR is enough. Revisit if a second consumer appears |
| Pin the contract here but skip the contract tests | A doc that isn't backed by a failing build is a wish, not a contract — the same "asserted, not measured" gap SYS-003 closed for the tool layer. The tests are what make the freeze real |
| Make the seam a shared library/import instead of HTTP, to get the shape "for free" from a shared type | Re-couples the repos into one release cycle and one runtime — the opposite of the deliberate HTTP decoupling; a typed wire contract + tests gets the safety without the coupling |

---

*Source of truth: classifier `src/api.py` (`ClassifyRequest` / `ClassifyResponse` + the
`/classify` 422/502 handler) and `src/classify.py` (`CATEGORIES`, `DOMAINS`); consumer
`kb-agent` `agent/tools.py` (`classify_snippet`). This ADR records the contract those
files currently implement and freezes it under the versioning rule above. Layers above
this one: [SYS-003](SYS-003-agent-tool-layer-contract.md) (agent-facing observation
envelope), [SYS-002](SYS-002-model-tier-standard.md) (model tier).*
