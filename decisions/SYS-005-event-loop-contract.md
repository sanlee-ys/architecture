# SYS-005: Close the classify-and-writeback loop — freeze the contract

**Status:** Accepted (updated 2026-06-27 — Kafka replaced by FastAPI BackgroundTasks; updated 2026-07-05 — classifier call now retries transient failures per SYS-013)
**Date:** 2026-06-23
**Deciders:** San Lee

---

## Context

`notes-api` needs to react to note creation by classifying the note's content and writing
predicted labels back as tags. The original implementation of this ADR used a Kafka
`NoteCreated` event flowing from `notes-api` (Spring Boot producer) to a `kafka-python`
consumer in `defense-news-classifier`. That implementation has been **replaced**: `notes-api`
was ported from Java/Spring Boot to Python/FastAPI, and the Kafka broker dependency was
dropped in favor of **FastAPI `BackgroundTasks`**.

The seam spans two repos and is owned by neither alone, so per `system/SYS-001`'s tiering
rule it is a **system** decision, not a repo-local one — the asynchronous sibling of
[SYS-004](SYS-004-classify-http-contract.md), which froze the *synchronous* `/classify`
HTTP seam between the classifier and `kb-agent`.

The forces remain the same: the classifier's tags must not clobber a user's own tags on the
note, and the writeback must be safe to re-run (idempotent). The delivery model changed from
at-least-once Kafka to a best-effort in-process background task — simpler to operate, with
the trade-off that a crashed worker loses the enrichment for that request (acceptable at
this scale; revisit if reliability SLA tightens).

## Decision

Close the classify-and-writeback loop via **FastAPI BackgroundTasks** in `notes-api`, and
freeze the contract below. Both repos are bound to it; neither may change it unilaterally
(see *Versioning rule*).

**Trigger.** Immediately after `POST /notes` returns `201 Created`, `notes-api` enqueues a
`BackgroundTask` (`classify_and_writeback(note_id, text)`, where `text` is the note's
title + content). The HTTP response to the caller is not delayed — the task runs after the
response is sent.

**Classification call.** The background task POSTs to the classifier's `/classify` endpoint:

```
POST {CLASSIFIER_URL}/classify
Content-Type: application/json
{ "text": "<title + content>" }
```

`CLASSIFIER_URL` is read from the environment. When unset (the default in dev/tests), the
task is a **no-op** — the enrichment is silently skipped so the API runs without a live
classifier. The response is the SYS-004 shape — **as of the classifier's `v3.0.0`
(2026-07-18) that is three fields**, `{ "category", "operational_domain", "region" }`, not the
two recorded when this ADR was written. **Corrected 2026-07-19:** this clause previously said
`region` was "currently ignored by this consumer." That is no longer true — notes-api consumes
all three fields (`notes-api/src/notes_api/tasks.py:44-48`), merged 2026-07-18. See the
[`SYS-004` amendment](SYS-004-classify-http-contract.md) for why the field reached production
ahead of the coordinated update its own contract required.

**Tag encoding.** The **three** predicted labels are written as **namespaced tags**:
`category:<category>`, `domain:<operational_domain>`, and `region:<region>` (e.g.
`category:procurement`, `domain:air`, `region:indo-pacific`). The namespace prefixes keep
machine tags distinct from a user's own tags and let the writeback safely replace only its own
prior tags on reprocessing.

The consumer derives its prefixes from the field map rather than hardcoding them
(`CLASSIFIER_PREFIXES`, `tasks.py:58`), which is why the `v3.0.0` addition required no
tag-specific code on this side. That is a property worth preserving: a fourth field would
again cost nothing here.

**Writeback.** *(Mechanism corrected 2026-07-18 — this section described an HTTP call the task
does not make.)* The background task writes **in-process through the ORM**, not over HTTP: it
opens a fresh session, loads the note via `NoteService`, merges tags, and commits
(`notes-api/src/notes_api/tasks.py:175-182`). A fresh session is required because the
request's session is closed once the response has been sent.

The `PUT /notes/{id}/tags` endpoint described below **does exist** (`notes-api/router.py:68`)
and carries the same replace semantics for external callers — returning `200` (the updated
note) / `404` (no such note) / `400` (validation). It is simply not the path the enrichment
loop takes, and this ADR previously conflated the two. What is frozen here is the **tag
encoding and replace semantics**; the transport is an implementation detail that differs
between the internal task and external callers.

The task writes the **merge** of the note's existing non-classifier tags plus
the two fresh classifier tags — so user tags are preserved and stale classifier tags are
replaced, never accumulated. The merge is capped at notes-api's 20-tag limit: the two
classifier tags always land, and the oldest user tags are dropped from *this writeback
snapshot* if a note is already at the cap — so a heavily-tagged note still gets classified
instead of the writeback failing with a 400.

**Idempotency (closes R1).** Because the writeback replaces a deterministic set and the
classifier tags are namespaced, re-running the task for the same note converges to the same
tags. Per SYS-013, a transient failure (connection error, timeout, 5xx) now retries with
backoff (3 attempts, 2s/4s) before giving up; a non-retryable failure (4xx, or any other
error shape) is logged and dropped immediately since retrying the same body won't help.
Retry is in-process only — a crashed worker still loses the enrichment for that request
(acceptable at this scale; a durable retry/dead-letter queue is the upgrade path if
reliability SLA tightens). A 404 (note deleted before writeback) is logged and skipped.

**`CLASSIFIER_URL` unset = no-op.** When the env var is absent, `classify_and_writeback`
returns immediately without making any HTTP call. This keeps the API fully functional in
development and test environments that have no live classifier.

**Versioning rule (mirrors SYS-004).** Changing the classifier request shape, the
tag-encoding scheme (the `category:`/`domain:` prefixes), or the writeback endpoint's
shape is a **breaking change to this contract**, requiring a coordinated change across both
repos landed together **plus** an update to this ADR (a new row or a superseding `SYS-NNN`).
The classifier's `v3.0.0` `region` field added exactly such a third namespaced tag
(`region:<…>`), gated by SYS-004 (the response field) and by this ADR (the tag). It
**shipped 2026-07-18** and is consumed in production. It is retained here as the worked
example of what this rule governs — and as the case where the coordinated update reached
production before the record did, which is the failure SYS-018 was written to prevent.

## Consequences

- **What this makes easier.** The loop is closed end to end with no broker to operate:
  create a note → it gets classified and tagged automatically, asynchronously, without
  coupling note creation to the classifier's availability. `CLASSIFIER_URL` unset is a safe,
  zero-friction default for local dev.
- **What it costs (the tradeoff accepted).** Best-effort delivery: if the `notes-api`
  worker process crashes between the `201` response and task completion, the enrichment is
  lost for that note. There is no durable queue or replay. Eventual consistency: a note's
  machine tags appear a moment after creation.
- **What we'll revisit.** If a reliability SLA emerges (e.g. "every note must be tagged"),
  the upgrade path is a durable task queue (Celery + Redis, or an outbox pattern) in place
  of BackgroundTasks — the writeback contract and the `PUT /notes/{id}/tags` endpoint are
  unchanged either way.
- **The writeback's next form.** Idempotency and the namespace-merge are currently the
  **caller's** job: the background task merges against the note's tags snapshot and `PUT`s the
  full set, which opens a lost-update window if a user edits tags between the task's read and its
  write. The documented upgrade path is a dedicated, classification-scoped
  **`PATCH /notes/{id}/classification`** that carries the two typed labels and does the
  strip-stale-then-upsert *inside notes-api*, against the note's **current** tags — so idempotency
  becomes a property of the **contract** rather than the caller, the lost-update window closes,
  and a second writeback path inherits the guarantee instead of re-implementing the merge.
  Deferred for v0 (the generic `PUT /tags` keeps notes-api a generic notes service and the
  caller-side merge already closes the loop); because it changes the writeback endpoint's shape it
  is a breaking change under the *Versioning rule* above — a coordinated change across both repos
  plus a superseding `SYS-NNN`.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Keep Kafka (the original design) | Requires operating a broker alongside the API; the Python port removed the Spring Boot infrastructure that made Kafka straightforward. BackgroundTasks achieves the same async decoupling at this scale with zero broker overhead |
| Synchronous classify-on-create (block the `POST /notes` response) | Couples note creation latency to the classifier's availability — a slow or unavailable classifier degrades the write path. Async keeps them independent |
| Consumer calls the classifier's `/classify` HTTP endpoint and also classifies internally | The background task is already in-process within `notes-api`; it calls the classifier's HTTP endpoint (SYS-004 seam), which is the right boundary — `notes-api` is the consumer, `defense-news-classifier` is the provider |
| Reuse `PUT /notes/{id}` (full note update) for writeback | Requires re-sending `title` + `content`, so a tag write could clobber a concurrent body edit, and it couples tagging to the whole note shape. A dedicated `PUT /notes/{id}/tags` is narrower and idempotent by construction |
| Append tags instead of replace | Not idempotent under reprocessing — re-running the task would accumulate duplicate/stale labels. Replace + namespaced prefixes converges |
| Write labels as plain tags (`procurement`, `air`) with no namespace | Indistinguishable from a user's own tags, so the task couldn't safely replace just its own on reprocessing, and a label could collide with a user tag. The `category:`/`domain:` namespace makes ownership explicit |
| Record this as a classifier-local ADR (or in notes-api) | The contract binds two repos and is owned by neither — `system/SYS-001` says that is a system decision |

---

*Source of truth: trigger — notes-api `src/notes_api/router.py` (`create_note`, `POST /notes`);
background task — notes-api `src/notes_api/tasks.py` (`classify_and_writeback`, plus the
`merge_tags` / `classifier_tags` helpers that namespace the labels and replace prior
classifier tags); writeback endpoint — notes-api `src/notes_api/router.py` (`set_tags`,
`PUT /notes/{id}/tags`) delegating to `src/notes_api/service.py` (`NoteService.set_tags`),
schemas in `src/notes_api/schemas.py` (`TagsRequest`); classifier endpoint —
`defense-news-classifier` `/classify`; label enums — classifier `src/classify.py`
(`CATEGORIES`, `DOMAINS`).
Related: [SYS-004](SYS-004-classify-http-contract.md) (the synchronous `/classify` seam,
same enums + versioning discipline), notes-api `ADR-001` (the producer half + the R1
idempotency mandate), [SYS-002](SYS-002-model-tier-standard.md) (model tier the task
classifies at), [SYS-013](SYS-013-self-healing-by-default.md) (the retry-and-visibility
mandate this update implements).*
