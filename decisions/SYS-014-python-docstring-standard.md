# SYS-014: Google-style docstrings as the Python docstring standard

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** San Lee

---

## Context

Docstrings had never been decided house-wide. A survey across the Python repos
(`defense-news-classifier`, `kb-agent`, `notes-api`, `learning-notes`,
`architecture`, plus the `dotfiles` and `career` scripts) found the shape had
already converged on its own: where docstrings exist, they use Google sections
(`Args:` / `Returns:` / `Raises:`) — `defense-news-classifier`, `kb-agent`, and
`notes-api` all do. **Zero** NumPy-style or reST/Sphinx field-list docstrings
were found anywhere. So this ADR is ratifying a de-facto standard, not imposing
a new one — the work is closing coverage gaps and turning the convention into
something a linter can hold, not converting between styles.

Two things the survey pinned down that shape the decision:

- **No repo publishes API docs.** Nothing runs Sphinx or `mkdocstrings` — the
  portal (`SYS-008`) aggregates hand-written Markdown, it does not render
  docstrings. So the value of a docstring here is **IDE hover-readability and
  lint-enforceability**, not generating a documentation site. That kills the
  one argument for reST (it only pays off under Sphinx).
- **No docstring linting exists yet.** `defense-news-classifier` and `notes-api`
  already run `ruff`, but neither has the `D` (pydocstyle) rules enabled. The
  convergence on Google style happened by habit, and habit drifts — a standard
  that isn't enforced where enforcement is cheap will erode.

The existing module docstrings also carry a deliberate **house pattern** richer
than plain PEP 257: they say what the module is, *why* it's shaped that way, and
where applicable give a `Run locally:` command (see `scripts/build_portal.py` in
this very repo). That pattern is an asset and predates this ADR — the standard
must preserve it, not flatten every module down to a one-line summary.

## Decision

Adopt **Google-style docstrings** (PEP 257 baseline) for all first-party Python
across the system. Concretely:

1. **Function/method docstrings use Google sections** (`Args:`, `Returns:`,
   `Raises:`, `Yields:`). First line is a one-line imperative summary ending in
   a period; a blank line precedes any further detail. **Types live in
   annotations, not repeated in the docstring** — write `text:`, never
   `text (str):`.
2. **One-liners are acceptable** where behavior is self-evident from the name
   and type hints — trivial helpers, health probes, dunder methods. Do not pad
   a trivial function with an empty `Args:` block.
3. **Module docstrings are required** on every first-party module. The existing
   house pattern (what the module is, why it's shaped this way, a `Run locally:`
   command where applicable) is **preserved, not rewritten** — only *missing*
   module docstrings get added.
4. **Coverage bar:** every public module, class, and public function/method with
   non-obvious behavior or non-self-evident parameters gets a full Google
   docstring. Private helpers may be one-liners. Test functions need **no**
   docstrings (the test name is the doc); test-module docstrings are optional.
5. **No NumPy style, no reST/Sphinx field lists** anywhere.
6. **Enforcement only where `ruff` already exists** (`defense-news-classifier`,
   `notes-api`): add `"D"` to ruff's lint `select` plus
   `[tool.ruff.lint.pydocstyle] convention = "google"`, with pragmatic ignores —
   `D1` (missing-docstring family) via per-file-ignores for `tests/**`, and
   `D105` (magic methods) / `D107` (`__init__`) ignored globally if they fire.
   **No new dependency is added to any repo that lacks `ruff`** to get this — see
   the `kb-agent` follow-up below.

## Consequences

- **What this makes easier.** Docstrings read consistently in the IDE across
  every repo, and the two `ruff` repos now *fail CI* on a missing or malformed
  docstring instead of relying on habit. New code inherits one answer instead of
  re-deciding per file.
- **What it costs.** A one-time coverage sweep per repo, and the two enforcement
  repos will surface a batch of `D` violations to clear on adoption. The ignore
  set (`tests/**`, `D105`, `D107`) is chosen so the bar lands on code that
  benefits, not on ceremony.
- **What it forecloses / defers.** `kb-agent` has no lint tooling, so enforcing
  `D` there would mean **introducing `ruff` as a new dev dependency** — out of
  scope for a docstring-standardization pass and deferred pending explicit
  sign-off (follow-up below). `learning-notes`, the `dotfiles` hooks, and the
  `career` scripts get the docstrings but no enforcement, for the same
  no-new-dependency reason.

### Follow-up

- **`kb-agent` `ruff` `D`-rule adoption is deferred** — it needs `ruff` added as
  a dev dependency, which is a separate decision requiring San's explicit
  sign-off. The docstrings land now; the enforcement waits.

## Alternatives Considered

| Option | Reason Not Chosen |
|--------|-------------------|
| **NumPy-style docstrings** | The vertical bulk (underlined `Parameters`/`Returns` sections) only pays off in array-heavy scientific APIs with many parameters — nothing in this system is that. It would be more typing for the same information Google style carries compactly. |
| **reST / Sphinx field lists** (`:param x:`) | Nearly unreadable raw in an IDE hover, and its one real payoff is generating a Sphinx site — which no repo here runs. All value would be deferred to a publishing step that doesn't exist. |
| **Leave it as a de-facto convention, no ADR, no linting** | The convergence on Google style happened by habit, and habit drifts. Where enforcement is nearly free (`ruff` is already installed in two repos), not enabling it leaves the standard to erode silently — the same "unenforced convention rots" failure this repo keeps writing ADRs to prevent. |
| **Enforce `D` everywhere, including `kb-agent`** | Would require adding `ruff` to a repo that has no lint tooling — a new dev dependency is a separate decision, and bundling it into a docstring pass violates scope discipline. Deferred to an explicit follow-up rather than smuggled in here. |
