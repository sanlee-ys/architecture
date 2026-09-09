# SYS-023: Each service owns an OTel span-name contract; a test fails on drift

**Status:** Accepted
**Date:** 2026-09-09
**Deciders:** San Lee

---

## Context

The three services emit OpenTelemetry spans today:

- `kb-agent`: `kb_agent.ask`, `chat {model}`, `execute_tool {tool}`
- `defense-news-classifier`: `chat {model}`
- `notes-api`: `classify_and_writeback`, `POST /classify`

Those names are strings in application code. No file lists them. A rename does
not fail a test. A dashboard or a SYS-019 claim that names "the kb-agent loop
span" then points at a name that no longer exists.

[`SYS-018`](SYS-018-provider-owned-contract-artifacts.md) already requires a
provider-owned artifact for HTTP response shapes. Span names are a second
shared surface. They are not HTTP fields. They have the same failure: two
copies of an assumption, and no build that turns red.

This decision is a Contract. A rename across services is an integration failure
for traces. It is not a local style choice.

## Decision

Each service owns `contracts/otel-spans.json`. A test in that service fails
when emitted span names drift from the file.

Rules:

1. **The service that emits a span owns the file.** This architecture repo
   does not own the names. Architecture CI does not clone the service repos
   to check them.
2. **The file is JSON.** It lists span names as strings under `span_names`.
   A static name is the exact string. A name with a runtime token uses a
   `{placeholder}` (example: `chat {model}`, `execute_tool {tool}`).
3. **The test records spans from a representative run** with an in-memory
   exporter. The test fails when the run emits a name that the file does not
   list. The test fails when the file lists a name that the run does not emit.
4. **The file is closed.** An added span is drift. The author updates the
   file in the same change as the new span.
5. **This contract pins names, not attributes.** Semantic-convention
   attributes (`gen_ai.*`, `http.*`) stay in code.

The three paths:

- `kb-agent/contracts/otel-spans.json`
- `notes-api/contracts/otel-spans.json`
- `defense-news-classifier/contracts/otel-spans.json`

Those files may land in later PRs in those repos. This decision is in force
when they land. Architecture CI does not wait for them and does not clone
those repos.

## Downstream surfaces

- `kb-agent/contracts/otel-spans.json` and its drift test (sibling repo; not
  in this PR)
- `notes-api/contracts/otel-spans.json` and its drift test (sibling repo; not
  in this PR)
- `defense-news-classifier/contracts/otel-spans.json` and its drift test
  (sibling repo; not in this PR)
- [`../program/README.md`](../program/README.md) — observability remaining work
- [`../engineering/README.md`](../engineering/README.md) — OTel next step
- [`../README.md`](../README.md) — log table row

**This list is a prompt for a sweep, not a guarantee that one happened**
(SYS-019). Architecture CI does not clone the three service repos, so it
cannot assert that those files exist.

## Consequences

- **What this makes easier.** A renamed span fails in the service that
  renamed it. Trace queries keep a stable name set.
- **What it costs.** Each service adds a contract file and a test. A new
  span needs a file edit in the same change.
- **What it forecloses.** Informal span names with no contract. A shared
  package of name constants. Ownership of names by this architecture repo.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **This architecture repo owns one combined schema** | Same reason SYS-018 rejected this: this repo cannot fail when a service changes a name. Architecture CI also must not clone the service repos. |
| **Rely on OpenTelemetry semantic conventions only** | The conventions cover attributes such as `gen_ai.*`. They do not pin the span names this system already emits. |
| **A scheduled job diffs traces after merge** | Drift is caught after the merge. SYS-018 rejected that shape for HTTP contracts. |
| **A shared Python package of span-name constants** | The package recouples the three runtimes. SYS-004 and SYS-018 rejected a shared package for contracts. |
| **Do nothing; keep names informal** | Claims about "the loop span" become unassertable. SYS-019 forbids a list that no test checks. |
