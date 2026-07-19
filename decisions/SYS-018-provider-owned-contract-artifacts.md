# SYS-018: Cross-repo contracts are enforced by a provider-owned artifact both sides assert against

**Status:** Accepted
**Date:** 2026-07-18
**Deciders:** San Lee

**Amends in practice:** [`SYS-004`](SYS-004-classify-http-contract.md), whose enforcement
claim this ADR replaces with a mechanism that works.

---

## Context

[`SYS-004`](SYS-004-classify-http-contract.md) froze the `/classify` wire contract and
stated that **"both sides now carry contract tests pinning this shape, so a drift is caught
by a red build."** [`SYS-005`](SYS-005-event-loop-contract.md) and
[`SYS-006`](SYS-006-notes-read-contract.md) rest on the same assumption, and the
[program risk register](../program/README.md#risk-register) recorded R8 (*"silent contract
drift"*) as **✅ Mitigated** on the strength of it.

It was not mitigated. On 2026-07-18 `defense-news-classifier` shipped `v3.0.0`, adding
`region` to the `/classify` response. `SYS-004`'s versioning rule requires a MAJOR bump
**and** a coordinated consumer update **and** an ADR update, together. Only the MAJOR bump
happened. `kb-agent` kept reading a two-field response for the rest of that day, and **no
build went red on either side.**

The mechanism matters more than the incident, because it was not a lapse — it was
structural. Each repo's "contract test" asserted its implementation against **its own copy
of the shape**:

- Provider: `defense-news-classifier/tests/test_api.py` — the fixture gained `"region"` in
  the same commit that shipped it. Correct behaviour for a unit test; useless as a contract
  test.
- Consumer: `kb-agent/tests/test_tools.py` — asserts against a stub the test file itself
  defines. It cannot observe the provider by construction.

Two unit tests that happen to agree are not a contract test. The only thing shared between
the suites was an assumption, and an assumption does not turn a build red when it becomes
false. This is precisely the option `SYS-004`'s own Alternatives table rejected — *"the wire
shape implicit, defined only by the two implementations"* — so the ADR rejected that design
and then, in implementation, shipped it. The word "contract" was doing work the tests were
not.

## Decision

**A frozen cross-repo contract is only frozen if there is one artifact both repos read.
The provider owns and publishes it; every consumer asserts against the published copy in
its own CI.**

Concretely, for each contract seam:

1. **The provider publishes a committed schema artifact**, generated from its live
   response model and label constants — never hand-edited, so it cannot describe a shape the
   service does not return. For `/classify` that is
   `defense-news-classifier/contracts/classify-response.schema.json`.
2. **The artifact is closed** (`additionalProperties: false`). This is what makes an *added*
   field a detectable breaking change rather than a silent one, and is the specific property
   whose absence let `region` through.
3. **The provider's CI fails on a stale artifact.** A generator runs in `--check` mode, so
   editing the response model or a label constant without regenerating turns the build red
   at the source, before a stale contract can reach a consumer.
4. **Each consumer fetches the published artifact in its own CI** and fails when its expected
   shape diverges. This is the outward-looking check; nothing else in a consumer repo can
   catch provider drift.
5. **Fetch failure is a warning, divergence is a failure.** A GitHub outage must not redden an
   unrelated build. The accepted cost is that an outage reads as a pass, so the warning is
   printed loudly rather than swallowed.
6. **One list per repo.** A consumer's expected field set lives in a single constant that both
   its runtime check and its contract check read. Two copies inside one repo is the same bug
   at smaller scale.

**The provider owns the artifact, not this repo.** The source of truth for a response shape
is the code that produces it. Publishing from there means the artifact cannot drift from the
implementation without failing the implementation's own build.

## Downstream surfaces

- [`SYS-004`](SYS-004-classify-http-contract.md) — its amendment banner records the breach and
  points here for the fix. Its "both sides carry contract tests" section is corrected.
- [`SYS-005`](SYS-005-event-loop-contract.md), [`SYS-006`](SYS-006-notes-read-contract.md) —
  **not yet covered.** Both freeze a seam with the same unenforced assumption. Applying this
  pattern to them is open work, named here so the gap is not silently inherited.
- [`../program/README.md`](../program/README.md) — R8 corrected from "✅ Mitigated" to
  materialized/open; it should move to mitigated once the `/classify` pair is merged.
- `portfolio` — `glossary.html`, `index.html`, `projects/the-system.html`,
  `projects/product-and-program.html` and `resume.html` all claimed CI catches renamed fields.
  Corrected 2026-07-18.
- `defense-news-classifier` — `contracts/`, `scripts/gen_contract_schema.py`,
  `tests/test_contract_schema.py`, `.github/workflows/tests.yml`, `CHANGELOG.md`.
- `kb-agent` — `scripts/check_classify_contract.py`, `tests/test_classify_contract_check.py`,
  `agent/tools.py` (`CLASSIFY_REQUIRED_FIELDS`), `.github/workflows/ci.yml`.

## Consequences

- **Drift becomes loud for the first time.** Verified rather than asserted, which matters
  given the failure being fixed is a guard that looked correct and did nothing: injecting a
  bogus enum value into the committed artifact turned two provider tests red; a simulated
  fourth provider field was caught by the consumer check with actionable guidance; an opened
  contract was caught.
- **The provider carries the publishing cost.** Regenerating the artifact is one command, but
  it is a step that did not exist, and forgetting it now fails the provider's build — which is
  the point, and also a real tax.
- **Consumers gain a network dependency in CI.** Mitigated by the warn-on-fetch-failure rule,
  at the stated cost of an outage reading as a pass.
- **This does not verify runtime behaviour.** It pins the *shape*, not that the service
  returns valid labels for a given input. A provider could satisfy the schema and still be
  wrong; that is what the eval harness is for.
- **`SYS-005` and `SYS-006` are now visibly unguarded.** Before this ADR they were equally
  unguarded but everyone believed otherwise, which was worse.
- **The two-repo assumption holds only while there is one consumer.** A second consumer of
  `/classify` would each need their own check; the pattern scales, the coordination cost
  grows.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **The architecture repo owns the schema** (neutral home, where the SYS ADRs live) | Conceptually tidy — the contract is a system-level thing — but it drags a third repo into every contract change, and this repo is not a package anyone installs. Worse, it puts the source of truth somewhere that cannot fail when the implementation diverges: the provider could change its model and architecture's build would stay green. Ownership belongs with the code that produces the shape |
| **Keep per-repo tests, add a scheduled cross-repo diff job** | Drift would be caught eventually rather than at the PR that causes it, which is the same "find out later" failure in slower form. A guard that fires after merge does not stop the merge |
| **A shared package both repos import the types from** | Gets the shape "for free" and is genuinely stronger — but it re-couples the repos into one release cycle and one runtime, which is exactly what `SYS-004` chose HTTP decoupling to avoid. A published artifact gets most of the safety without the coupling |
| **Consumer vendors a copy of the schema, no fetch** | No network dependency, but it is two copies again — precisely the failure being fixed, with an extra file to forget |
| **Contract-testing framework (Pact or similar)** | Real consumer-driven contract testing with a broker. Correct at team scale and substantial infrastructure for one provider and one consumer in a personal system. Revisit if a second consumer appears |
| **Fail the consumer build on fetch failure too** | Strictly safer against a deleted artifact, but makes every consumer build depend on GitHub being up. Chose the asymmetry deliberately and documented what it costs |
| **Do nothing; treat the incident as a one-off lapse** | It was not a lapse. Nothing in either repo *could* have caught it — the failure was structural, and leaving it would mean the next breaking change is equally silent |
