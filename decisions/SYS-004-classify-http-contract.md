# SYS-004: Freeze the /classify HTTP contract between the classifier and kb-agent

**Status:** Accepted — **amended 2026-07-18: the contract is currently BREACHED; the guard this ADR claimed did not fire**
**Date:** 2026-06-22 (amended 2026-07-18)
**Deciders:** San Lee

---

> **Amendment, 2026-07-18 — the worked example happened, and nothing stopped it.**
>
> This ADR named the `region` field as "exactly the change this rule exists to gate" and said
> it "may not ship on the provider alone." On 2026-07-18 it shipped on the provider alone.
> `defense-news-classifier` released `v3.0.0` with `region` on the `/classify` response
> (`src/api.py:63`); `kb-agent/agent/tools.py` contains **no** occurrence of `region`. Of the
> three things the versioning rule requires to move together, only condition 1 (the MAJOR
> bump) happened. Condition 2 (coordinated consumer update) is outstanding — verified
> 2026-07-18: no `region` branch and no open `region` PR on `sanlee-ys/kb-agent`. Condition 3
> is this amendment.
>
> **Why no build went red — the mechanism, not the excuse.** The claim below that "both sides
> now carry contract tests pinning this shape" is true only in a sense that turns out to be
> worthless. Each side asserts against **its own private copy** of the shape:
> the provider test's fixture was updated to include `"region"` in the same change that
> shipped it (`defense-news-classifier/tests/test_api.py:41,51`), and the consumer test
> asserts against a hand-written stub body it controls
> (`kb-agent/tests/test_tools.py:160,275`). Neither imports a shared artifact; neither
> observes the other. Two unit tests that happen to agree are not a contract test. That is
> precisely the option this ADR's own Alternatives table rejected as the status quo —
> *"the wire shape implicit, defined only by the two implementations"* — so the ADR rejected
> that design and then, in implementation, shipped it.
>
> **The load-bearing clause is currently false.** "Exactly these two fields" (below) does not
> describe the deployed provider. The clause is left in place, struck through in effect by
> this banner rather than quietly rewritten, because the gap between what it says and what
> runs is the finding.
>
> **What closes this** is a single shared contract artifact both repos assert against, so
> changing one copy fails the other's build. That mechanism is now decided and specified in
> [`SYS-018`](SYS-018-provider-owned-contract-artifacts.md): the **provider** owns and
> publishes a generated, closed schema artifact, its own CI fails on a stale one, and each
> consumer fetches the published copy and fails on divergence. Until both halves are merged
> this ADR remains a description rather than a guard, and any surface claiming CI catches
> `/classify` drift is over-claiming (see the
> [program risk register](../program/README.md#risk-register), R8).

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
  **⚠️ Currently false in production as of 2026-07-18** — the deployed provider returns a
  third field, `region` (see the amendment banner above). Retained as written so the breach
  is legible rather than papered over; it is re-frozen at three fields only when the
  coordinated `kb-agent` update lands.
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

The concrete worked example was the classifier's **`v3.0.0` `region` field**: the response
becomes `{category, operational_domain, region}`, which adds a field and therefore breaks
this contract. It was exactly the change this rule existed to gate — it could not ship as a
minor or a patch, and it could not ship on the provider alone.

**It shipped on the provider alone, on 2026-07-18.** The rule was not enforced by anything;
it was a sentence. Condition 1 (MAJOR bump) held because the classifier's own semver
discipline is good. Condition 2 (coordinated consumer update) did not happen and nothing
noticed. This is no longer a worked example — it is the case study in why a versioning rule
without a shared, cross-repo assertion is documentation of an intention.

Non-breaking changes — adding a *new* endpoint, loosening the char cap, improving an
error `detail` string — keep the contract intact and need only the ordinary minor/patch
treatment.

**Both sides carry tests pinning this shape — but they pin it independently, which is the
flaw** (corrected 2026-07-18; the original text claimed drift "is caught by a red build,"
and the `region` breach proved otherwise):

- **Provider (`defense-news-classifier`):** a test pins `ClassifyResponse`'s fields and the
  enums to `CATEGORIES`/`DOMAINS`, and the API tests assert the 200 body shape plus bad
  input → 422 / upstream failure → 502. **But the assertion is against the provider's own
  model**, so when the provider changed, the test changed with it in the same commit
  (`tests/test_api.py:41,51` now carry `"region"`). It stayed green through a breaking
  change, which is the correct behavior for a unit test and the wrong behavior for a
  contract test.
- **Consumer (`kb-agent`):** a test asserts `classify_snippet` parses the 200 shape into its
  SYS-003 `payload`, and that a body missing a field degrades to a SYS-003 error observation
  rather than crashing the loop. **But the 200 body it parses is a hand-written stub the
  test itself defines** (`tests/test_tools.py:160,275`), so it asserts the consumer matches
  the consumer's own belief about the provider. It cannot observe the provider changing.

Both repos run these in CI, so each implementation is enforced against **itself** on every
push. Neither is enforced against the other. The word "contract" in "contract test" was
doing work here that the tests were not: the only thing shared between the two suites was an
assumption, and an assumption does not turn a build red when it becomes false.

**The gap, stated plainly so the fix is unambiguous:** there is no artifact that both repos
read. Closing it requires one — a committed JSON Schema or golden response fixture, owned by
one side and asserted against by both, so that a field added on the provider fails the
consumer's build. Until that exists this section describes two unit suites, not a guard.

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

- ~~**Drift is now loud, not silent.**~~ **Falsified 2026-07-18.** The exact failure the
  risk register named — the provider changing the wire shape while the consumer keeps
  reading the old one — happened, and no build went red on either side. The consequence as
  originally written described what the author intended the tests to do, not what they
  assert. Drift is currently **silent**, and the risk register entry claiming otherwise (R8)
  is corrected in the same pass as this amendment.
- ~~**The `region` change has a defined, gated path.**~~ **Falsified 2026-07-18.** It had a
  defined path and no gate. `v3.0.0` did ship with the MAJOR bump the rule demanded, so the
  half of the rule backed by the classifier's own semver discipline held; the half that
  required another repo to move had nothing enforcing it. A rule that spans two repos and
  lives in neither one's build is a convention, whatever the ADR calls it.
- **The two repos stay decoupled, deliberately.** The seam is still HTTP and
  config-driven, not a shared import or package — each keeps its own environment and
  release cycle. The contract is the coupling; the code is not.
- **It costs coordination on breaking changes.** A response-shape change can no longer be
  a one-repo edit — that friction is the *point* (it's what makes the consumer safe), but
  it is a real tax on the provider, paid now while there is exactly one consumer.
- **The contract must be kept in step with the code.** If `src/api.py` or the enums in
  `src/classify.py` change, this ADR is stale until updated — the same revisit obligation
  SYS-002 and SYS-003 carry. ~~The contract tests are the tripwire that this happened.~~
  **There was no tripwire.** `src/api.py` changed on 2026-07-18 and this ADR sat stale for
  the rest of that day until an unrelated audit read it. The revisit obligation was carried
  by memory, which is the thing ADRs exist to replace.

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
