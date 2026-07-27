"""Failure-path regression tests for the decision-log lint.

WHY THESE EXIST. Same reason as the metrics guard's tests next door: in CI this linter is
only ever *run against this repo's real content*, where it is expected to pass. That
exercises the happy path and leaves every failure branch — the drift detection that is the
entire point — unexecuted. A check can quietly stop checking and the build stays green,
which is the failure mode the linter's own docstring is written about.

The drift classes below were originally found by a two-tier audit costing 35 agents and
2.8M tokens. The linter made re-finding them cost nine seconds. These tests are what keeps
that true: each one injects exactly one of the audit's findings into a synthetic log and
asserts the linter still sees it.

WHAT IS STUBBED. The whole repo. `REPO_ROOT`, `DECISIONS`, `ADRS` and `README` are
module-level `Path` globals, so a tmpdir can be substituted for all four. Using a synthetic
log rather than the real one matters here: these tests must not start failing because
somebody legitimately added a decision, and a fault must be injectable without editing
tracked documents.

These tests pin CURRENT behaviour. If a rule is deliberately changed, change the test in
the same commit and say why.
"""

from __future__ import annotations

import pytest

import lint_decision_log as lint_mod

# A structurally complete decision document: status header, a populated Alternatives table
# (the promotion bar's second prong), and the mandatory Downstream surfaces section.
DOC = """# SYS-050: A thing

**Status:** Accepted

## Alternatives Considered

| Option | Why not |
| --- | --- |
| Do nothing | Drift continues |
| Do it elsewhere | Wrong repo |

## Downstream surfaces

None.
"""

README = """# Decisions

| ID | Status |
| --- | --- |
| [SYS-050](decisions/SYS-050-a-thing.md) | Accepted |
"""


@pytest.fixture
def repo(monkeypatch, tmp_path):
    """Build a synthetic, clean decision log and point the linter at it.

    Returns the root so each test can inject exactly one fault. Defaults are clean, so a
    passing assertion is evidence that the *injected* fault is what tripped the check.
    """
    (tmp_path / "decisions").mkdir()
    (tmp_path / "adr").mkdir()
    (tmp_path / "decisions" / "SYS-050-a-thing.md").write_text(DOC, encoding="utf-8")
    (tmp_path / "README.md").write_text(README, encoding="utf-8")

    monkeypatch.setattr(lint_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lint_mod, "DECISIONS", tmp_path / "decisions")
    monkeypatch.setattr(lint_mod, "ADRS", tmp_path / "adr")
    monkeypatch.setattr(lint_mod, "README", tmp_path / "README.md")
    monkeypatch.setattr(lint_mod, "LEGACY_NO_DOWNSTREAM", set())
    return tmp_path


def test_clean_log_passes(repo):
    """The baseline. A linter that always fails is an outage, not a guard."""
    assert lint_mod.lint() == []


def test_doc_with_no_table_row_is_caught(repo):
    """`SYS-016` was cited from two documents while having no row in the log table.

    A doc nobody can find in the index gets cited from memory, which is how three surfaces
    ended up citing a wrong SYS number for evals-as-CI.
    """
    (repo / "decisions" / "SYS-051-unindexed.md").write_text(
        DOC.replace("SYS-050", "SYS-051"), encoding="utf-8"
    )
    assert any("SYS-051 exists on disk but has NO ROW" in p for p in lint_mod.lint())


def test_table_row_with_no_file_is_caught(repo):
    """The mirror image: an index entry pointing at nothing."""
    (repo / "README.md").write_text(
        README + "| [SYS-052](decisions/SYS-052-ghost.md) | Accepted |\n", encoding="utf-8"
    )
    assert any("README.md lists SYS-052 but no such file exists" in p for p in lint_mod.lint())


def test_status_drift_between_table_and_header_is_caught(repo):
    """`SYS-009` showed `Proposed` in the table for three weeks while its header said
    `Accepted`. Two sources of truth for one fact, and nothing comparing them."""
    (repo / "README.md").write_text(README.replace("| Accepted |", "| Proposed |"), "utf-8")
    assert any("the log table says 'Proposed'" in p for p in lint_mod.lint())


def test_status_decoration_is_not_read_as_drift(repo):
    """The other half: the comparison must tolerate the decoration each side legitimately
    carries — amendment prose on headers, emphasis and warning markers in cells.

    Without this, every amended decision reads as drift, the check becomes noise, and a
    check that cries wolf gets silenced. That failure is quieter than a missed drift and
    strictly worse.
    """
    (repo / "decisions" / "SYS-050-a-thing.md").write_text(
        DOC.replace("**Status:** Accepted", "**Status:** Accepted - amended 2026-07-18: scope"),
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        README.replace("| Accepted |", "| WARN **Accepted - BREACHED** |"), encoding="utf-8"
    )
    assert lint_mod.lint() == []


def test_unresolvable_relative_link_is_caught(repo):
    """Re-tiering moves a document out from under every relative link inside it; `ADR-001`
    shipped with exactly that break."""
    (repo / "decisions" / "SYS-050-a-thing.md").write_text(
        DOC + "\nSee [the other one](SYS-999-nowhere.md).\n", encoding="utf-8"
    )
    assert any("relative link 'SYS-999-nowhere.md' does not resolve" in p
               for p in lint_mod.lint())


def test_empty_alternatives_table_is_caught(repo):
    """The promotion bar's second prong is that a decision FORECLOSES something. An
    Alternatives table with no option rows means it did not, so it is not a decision."""
    (repo / "decisions" / "SYS-050-a-thing.md").write_text(
        DOC.replace("| Do nothing | Drift continues |\n| Do it elsewhere | Wrong repo |\n", ""),
        encoding="utf-8",
    )
    assert any("'Alternatives Considered' is missing or has no option rows" in p
               for p in lint_mod.lint())


def test_missing_downstream_surfaces_is_caught(repo):
    """`TEMPLATE.md` and the README both call this section mandatory; it was present in 2
    of 17 documents. 'None' is a valid answer but must be written."""
    (repo / "decisions" / "SYS-050-a-thing.md").write_text(
        DOC.replace("## Downstream surfaces\n\nNone.\n", ""), encoding="utf-8"
    )
    assert any("missing '## Downstream surfaces'" in p for p in lint_mod.lint())


def test_grandfathered_doc_may_omit_downstream_surfaces(repo, monkeypatch):
    """The ratchet's other half. SYS-001's own shape list omitted this section until
    2026-07-18, so an author following the practice literally produced a non-compliant
    document — the fault was the instruction. Grandfathered rather than backfilled; if the
    allowance stopped working the pressure would be to churn already-cited documents."""
    monkeypatch.setattr(lint_mod, "LEGACY_NO_DOWNSTREAM", {"SYS-050"})
    (repo / "decisions" / "SYS-050-a-thing.md").write_text(
        DOC.replace("## Downstream surfaces\n\nNone.\n", ""), encoding="utf-8"
    )
    assert lint_mod.lint() == []


def _add_tombstone(root):
    """Retire SYS-051 into adr/ADR-009, leaving a tombstone and an indexed row.

    A tombstone keeps existing citations resolving (SYS-001's narrowed retroactivity rule),
    which is what makes the retired-number sweep necessary: the number stays valid, so
    nothing else forces the rest of the repo to be swept.
    """
    (root / "decisions" / "SYS-051-old.md").write_text(
        "# SYS-051: Old\n\n**Status:** Moved to [ADR-009](../adr/ADR-009-new.md)\n",
        encoding="utf-8",
    )
    (root / "adr" / "ADR-009-new.md").write_text(
        "# ADR-009: New\n\n**Status:** Accepted\n", encoding="utf-8"
    )
    (root / "README.md").write_text(
        README + "| [SYS-051](decisions/SYS-051-old.md) | Moved |\n\nSYS-051 moved to ADR-009.\n",
        encoding="utf-8",
    )


def test_retired_citation_without_successor_is_caught(repo):
    """The 2026-07-18 re-tiering left five stale citations behind, two of them rendered to
    readers — with this lint green the whole time, because it read `decisions/` and the log
    table and said nothing about the rest of the repo citing them."""
    _add_tombstone(repo)
    (repo / "notes.md").write_text("Per SYS-051, the seam is contractual.\n", encoding="utf-8")
    assert any("cites retired 'SYS-051' and never names where it went" in p
               for p in lint_mod.lint())


def test_retired_citation_naming_its_successor_passes(repo):
    """Deliberately loose: a file may cite a retired number freely as long as it also names
    the successor. That is what separates a tombstone, a log row or a footnoted historical
    record from a surface nobody swept — and a stricter rule would ban the honest forms."""
    _add_tombstone(repo)
    (repo / "notes.md").write_text(
        "Per SYS-051 (now ADR-009), the seam is contractual.\n", encoding="utf-8"
    )
    assert lint_mod.lint() == []


def test_tombstone_without_a_destination_is_caught(repo):
    """A redirect to nothing is worse than no redirect, because it looks handled."""
    _add_tombstone(repo)
    (repo / "decisions" / "SYS-051-old.md").write_text(
        "# SYS-051: Old\n\n**Status:** Moved\n", encoding="utf-8"
    )
    assert any("no link to a destination outside decisions/" in p for p in lint_mod.lint())
