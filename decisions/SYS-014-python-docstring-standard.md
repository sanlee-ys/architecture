# SYS-014: Google-style docstrings — RE-TIERED TO A CONVENTION

**Status:** Moved — now a house convention in [`engineering/README.md`](../engineering/README.md)
**Date:** 2026-07-05 (re-tiered 2026-07-18)
**Deciders:** San Lee

---

## This number is retired

The docstring standard is now a bullet in the **Cross-repo engineering standards** section of
[`engineering/README.md`](../engineering/README.md). The enforceable specifics already lived
where they belong — `ruff`'s `D` rules with `convention = "google"` in each Python repo's
`pyproject.toml`. **`SYS-014` is never reused.**

This tombstone exists so every existing citation keeps resolving, per
[`SYS-001`](SYS-001-record-architecture-decisions.md)'s narrowed retroactivity rule.

## Why it moved

It is a **convention**, not a decision, by `SYS-001`'s own definition — and the clearest
evidence is its own text: it described itself as *"ratifying a de-facto standard, not imposing
a new one."* A survey found **zero** NumPy-style or reST docstrings anywhere to convert. The
rejected alternatives do not cost anything real: reST's payoff requires a Sphinx site no repo
runs, "leave it unenforced" is the null option, and the fourth row *deferred* `kb-agent`
rather than rejecting it — a deferral since decided the opposite way, as `kb-agent` now
selects the `D` rules too.

It crosses repos, so it clears prong 1. It forecloses nothing, so it fails prong 2.

## The argument that had to be answered

This document is CI-enforced in three repos — a breach fails a build — which was used to argue
it belongs at system altitude. `SYS-001`'s own correction, written about this exact document,
answers it: **enforcement is the wrong axis to sort a decision log by.** Enforcement is a
property of this month's tooling; altitude is about what a decision forecloses. A lint rule
that fails builds in three repos is still a lint rule.

`SYS-001`'s promotion-bar amendment continues to cite `SYS-014` as its worked example of a
convention sitting at contract altitude. That citation is left in place and reads better after
the move, not worse.
