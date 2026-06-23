# SYS-006: Freeze the GET /notes read contract between kb-agent and notes-api

**Status:** Accepted
**Date:** 2026-06-23
**Deciders:** San Lee

---

## Context

`kb-agent` gained a second cross-repo tool, `search_notes`, that reads the user's live
notes from `notes-api` over HTTP — the agent's `GET /notes` consumer. This is the
**read** sibling of [SYS-004](SYS-004-classify-http-contract.md) (which froze the
synchronous `/classify` seam between `kb-agent` and the classifier) and it closes the
last unbuilt edge in the program dependency map: `kb-agent → notes-api`.

Like SYS-004, this is a contract that spans two repos with separate release cycles, so
it is owned by neither and is recorded at the **system** tier (`system/SYS-001`). The
risk is the same one R8/SYS-004 named: the provider (`notes-api`) could rename a field
or change the response shape, and the consumer (`kb-agent`) would silently mis-read it
at runtime. This ADR freezes the read shape and ties the versioning rule to it.

**Source of truth (read *from* the code, not invented here):**

- Provider — `notes-api` `controller/NoteController.java` (`getAll`, `GET /notes` with
  optional `?q=` and `?tag=`) and `dto/NoteResponse.java` (the response record).
- Consumer — `kb-agent` `agent/tools.py` (`search_notes`, which GETs `{base}/notes`
  with `q`/`tag` params and reads `id`/`title`/`content`/`tags` out of each element).

## Decision

Adopt the following as the **frozen `GET /notes` read contract**. Both repos are bound
to it; neither may change it unilaterally (see *Versioning rule*).

**Endpoint.** `GET {base}/notes`, where `{base}` is the `notes-api` base URL supplied to
`kb-agent` via the `notes-api` entry in `projects.yaml` (config, not code).

**Query (optional).**

- `q` — free-text substring matched in title/content.
- `tag` — exact tag to require.
- With neither, returns all notes. Blank values are treated as absent.

**Success response — HTTP 200 (JSON).** A **JSON array** of note objects; each carries
at least:

```json
{ "id": <number>, "title": "<string>", "content": "<string>", "tags": ["<string>", …] }
```

- The body is an **array** (possibly empty), not an object — the load-bearing clause the
  consumer relies on. `notes-api` also returns `createdAt`/`updatedAt`; `kb-agent` reads
  only `id`/`title`/`content`/`tags` and ignores the rest, so *adding* response fields is
  non-breaking.

**Errors / empties.** A non-200, a non-JSON body, or a non-array 200 is a service-side
problem; `kb-agent`'s `search_notes` surfaces each as a SYS-003 *error* observation (never
a raised exception), and an empty array as a SYS-003 *warning*.

**Versioning rule (mirrors SYS-004).** Removing or renaming `id`/`title`/`content`/`tags`,
or changing the 200 from an array to some other shape, is a **breaking change to this
contract**, requiring a coordinated change across both repos landed together **plus** an
update to this ADR. Adding a new response field, or a new optional query param, is
non-breaking (the consumer ignores unknown fields).

**Both sides carry tests for their half.** `kb-agent` has a `search_notes` contract suite
(happy path + every failure mode → SYS-003 observation, all through the `_obs()` grader);
`notes-api` has controller/response tests pinning the `GET /notes` shape. (Unlike a single
process, there is no cross-repo live contract test on this read seam — each side tests its
own end; a live round-trip is the same residual the event-loop seam tracks in SYS-005.)

**Relationship to SYS-003 and SYS-004.** SYS-003 governs the *agent-facing* observation
envelope `search_notes` returns to the model; SYS-006 governs the *HTTP wire shape*
underneath it — exactly the two-layer split SYS-004 drew for the classify seam.
`search_notes` is where they meet, translating a `GET /notes` response into a SYS-003
observation.

## Consequences

- **The dependency map is now fully wired.** Both `kb-agent` tool seams
  (`→ classifier`, `→ notes-api`) exist and are contract-frozen; the agent reads the
  knowledge base through the service that owns it, not only through static stubs.
- **Drift is loud, not silent** — the same guarantee as SYS-004, now on the read seam.
- **The repos stay decoupled** — HTTP + config, not a shared import or a shared DB.
- **What we'll revisit.** The read is unauthenticated and unpaginated: `GET /notes`
  returns *all* matches, so `search_notes` can return a large payload for a broad query.
  Acceptable at personal-KB scale; revisit with a `limit`/pagination param (a non-breaking
  add under this contract) if note volume grows. Auth is a notes-api-wide concern, tracked
  there.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| Index notes-api's content into kb-agent's ChromaDB instead of a live read | Stale by construction and re-introduces a copy of the data; the point of the seam is to read the *owning* service live. The static stub (`kb/projects/notes-api.md`) already covers "describe the project" |
| Share a database or a library between kb-agent and notes-api | Re-couples two independently-released repos into one runtime — the opposite of the deliberate HTTP decoupling SYS-004 also rejected |
| Leave the read shape implicit (status quo before this ADR) | The "silent drift" risk: notes-api could change `GET /notes` and kb-agent would mis-read it with nothing failing until runtime |
| Record this as a kb-agent-local or notes-api-local ADR | The contract binds two repos and is owned by neither — `system/SYS-001` puts that at the system tier (same call as SYS-004) |

---

*Source of truth: provider — notes-api `controller/NoteController.java` (`getAll`) and
`dto/NoteResponse.java`; consumer — kb-agent `agent/tools.py` (`search_notes`). Siblings:
[SYS-004](SYS-004-classify-http-contract.md) (the synchronous classify seam, same
versioning discipline), [SYS-003](SYS-003-agent-tool-layer-contract.md) (the observation
envelope `search_notes` returns), [SYS-005](SYS-005-event-loop-contract.md) (the async
event-loop seam).*
