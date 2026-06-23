# SYS-005: Close the note-events loop — freeze the consume + tags-writeback contract

**Status:** Accepted
**Date:** 2026-06-23
**Deciders:** San Lee

---

## Context

`notes-api` already publishes a `NoteCreated` event to the `note-events` Kafka topic
whenever a note is created (notes-api `ADR-001`). That was the *producer* half of the
event loop; the *consumer* half — something that reads those events, classifies the
note, and writes tags back — did not exist. The loop was open: events flowed into the
topic and nothing acted on them.

This ADR closes that loop and freezes the cross-repo contract for it. The seam spans
two repos and is owned by neither alone, so per `system/SYS-001`'s tiering rule it is a
**system** decision, not a repo-local one — the asynchronous sibling of
[SYS-004](SYS-004-classify-http-contract.md), which froze the *synchronous* `/classify`
HTTP seam between the classifier and `kb-agent`.

The forces: delivery is **at-least-once** (notes-api `ADR-001` accepts the dual-write
problem), so the same event can arrive more than once — the consumer must be
**idempotent** (the program risk register's **R1**). And the classifier's tags must not
clobber a user's own tags on the note.

## Decision

Add a **Kafka consumer to `defense-news-classifier`** (`src/consumer.py`) that closes
the loop, and freeze the contract below. Both repos are bound to it; neither may change
it unilaterally (see *Versioning rule*).

**The event (consumed).** Topic **`note-events`**, key = note id as a string, value =
the JSON `NoteCreated` fat event — `{ id, title, content, tags, createdAt }`, **no Kafka
type headers** (`spring.json.add.type.headers=false`). The consumer decodes the value as
UTF-8 JSON; it needs `id` (to write back), and `title` + `content` (the text to classify).

**Classification.** The consumer calls the classifier's **core `classify()` in-process**
— *not* the `/classify` HTTP endpoint — reusing the same model tier (`system/SYS-002`)
and the same frozen label enums as SYS-004: `category ∈ {procurement, operations, policy,
technology, industry}`, `operational_domain ∈ {air, land, sea, cyber, space, multi}`.

**Tag encoding.** The two predicted labels are written as **namespaced tags**:
`category:<category>` and `domain:<operational_domain>` (e.g. `category:procurement`,
`domain:air`). The namespace prefixes keep machine tags distinct from a user's own tags
and let the consumer recognise — and replace — its own prior tags on reprocessing.

**Writeback.** `PUT {notes-api}/notes/{id}/tags` with body `{ "tags": [<string>, …] }`,
**replace semantics**, returning `200` (the updated note) / `404` (no such note) / `400`
(validation). The consumer sends the **merge** of the note's existing non-classifier tags
plus the two fresh classifier tags — so user tags are preserved and stale classifier tags
are replaced, never accumulated. The merge is **capped at notes-api's 20-tag limit**
(`TagsRequest`/`NoteRequest` `@Size(max=20)`): the two classifier tags always land, and the
oldest user tags are dropped from *this writeback snapshot* (never from the note itself) if a
note is already at the cap — so a heavily-tagged note still gets classified instead of the
writeback failing with a 400.

**Idempotency (closes R1).** Because the writeback replaces a deterministic set and the
classifier tags are namespaced, applying the same event repeatedly converges to the same
tags. The consumer commits the Kafka offset **only after** classify *and* writeback both
succeed; a transient failure (LLM/network error, notes-api `5xx`) leaves the offset
uncommitted so the message is redelivered, and a poison message (an unclassifiable note,
or a `4xx` such as a deleted note) is logged and skipped so it cannot wedge the partition.

**Versioning rule (mirrors SYS-004).** Changing the `NoteCreated` field set, the
`note-events` topic/key, the tag-encoding scheme (the `category:`/`domain:` prefixes), or
the writeback endpoint's shape is a **breaking change to this contract**, requiring a
coordinated change across both repos landed together **plus** an update to this ADR (a new
row or a superseding `SYS-NNN`). The classifier's roadmapped `v3.0.0` `region` field would
add a third namespaced tag (`region:<…>`) and is exactly such a coordinated change — it is
gated by SYS-004 (the response field) and by this ADR (the tag).

## Consequences

- **What this makes easier.** The loop is closed end to end: create a note → it gets
  classified and tagged automatically, asynchronously, without coupling note creation to
  the classifier's availability. New consumers (a search indexer, analytics) can join
  `note-events` later without notes-api knowing.
- **What it costs (the tradeoff accepted).** A second long-running process (the consumer)
  now has to be operated alongside the API and the broker — no production deployment story
  yet (local only). Eventual consistency: a note's machine tags appear a moment after
  creation. The writeback uses the **event's tags snapshot**, so a user edit to tags made
  between create and processing could be momentarily overwritten by the merge — accepted at
  this scale (the fat event exists precisely so the consumer need not call back).
- **What we'll revisit.** The async seam is **not yet covered by a live-broker contract
  test** the way SYS-004's HTTP seam is on both sides — the consumer logic is unit-tested
  (idempotency, tag encoding, poison/transient handling) and the writeback endpoint is
  unit-tested, but nothing exercises a real `note-events` round trip in CI. That is the
  residual drift risk on this seam (the async cousin of R8), to close with an integration
  test (e.g. Testcontainers Kafka) when the loop graduates past local.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Consumer calls the classifier's `/classify` HTTP endpoint instead of the core function | Adds a network hop and a second failure mode inside the same repo for no gain — the consumer already runs in the classifier's process and can import `classify()` directly. HTTP is the right seam for *cross-repo* callers (kb-agent), not for the classifier calling itself |
| Reuse `PUT /notes/{id}` (full note update) for writeback | It requires re-sending `title` + `content`, so a tag write could clobber a concurrent body edit, and it couples tagging to the whole note shape. A dedicated `PUT /notes/{id}/tags` is narrower and idempotent by construction |
| Append tags instead of replace | Not idempotent under at-least-once delivery — redelivery would accumulate duplicate/stale labels, the exact failure R1 names. Replace + namespaced prefixes converges |
| Write labels as plain tags (`procurement`, `air`) with no namespace | Indistinguishable from a user's own tags, so the consumer couldn't safely replace just its own on reprocessing, and a label could collide with a user tag. The `category:`/`domain:` namespace makes ownership explicit |
| Record this as a classifier-local ADR (or in notes-api) | The contract binds two repos and is owned by neither — `system/SYS-001` says that is a system decision. A repo-local record would hide a cross-repo contract inside one side, the anti-pattern SYS-004 also rejected |
| `@TransactionalEventListener` / outbox on the producer now | That hardens the *publish* side (notes-api `ADR-001` already names the outbox as its upgrade path); it is orthogonal to closing the *consume* side, which is what this ADR does |

---

*Source of truth: producer — notes-api `event/NoteCreated.java`, `service/NoteService.java`
(`create`), `resources/application.properties` (serializer + topic); writeback — notes-api
`controller/NoteController.java` (`updateTags`), `service/NoteService.java` (`setTags`),
`dto/TagsRequest.java`; consumer — classifier `src/consumer.py` (`process_event`,
`merge_tags`, `make_writeback_fn`); label enums — classifier `src/classify.py`
(`CATEGORIES`, `DOMAINS`). Related: [SYS-004](SYS-004-classify-http-contract.md) (the
synchronous `/classify` seam, same enums + versioning discipline), notes-api `ADR-001`
(the producer half + the R1 idempotency mandate), [SYS-002](SYS-002-model-tier-standard.md)
(model tier the consumer classifies at).*
