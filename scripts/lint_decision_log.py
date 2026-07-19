"""Lint the decision log: catch the drift classes an audit had to find by hand.

On 2026-07-18 a two-tier audit of 38 decision documents found, among other
things: `SYS-016` cited from two docs with **no row in the log table**;
`SYS-009` showing `Proposed` in that table for three weeks while its own header
said `Accepted`; three surfaces citing a *wrong* SYS number for evals-as-CI; and
`Downstream surfaces` — a section `TEMPLATE.md` and the README both call
mandatory — present in 2 of 17 documents.

Every one of those is mechanically checkable, and every one was found by luck and
timing instead. Finding them cost 35 agents and 2.8M tokens. Re-finding them
should cost nine seconds.

This is the same move as `SYS-018`, turned on the log itself: the rules stop being
behavioural and start being executable. The lesson of that whole day was that a
rule without a mechanical backstop drifts silently, and a decision log is not
exempt from its own finding.

Checks
------
1. Every `decisions/SYS-*.md` on disk has a row in `README.md`'s log table.
2. Every table row points at a file that exists.
3. The table's Status cell matches the document's own `**Status:**` header.
4. Relative Markdown links between decision docs resolve.
5. Every doc has a non-empty `Alternatives Considered` table (the promotion bar's
   second prong is "it forecloses something" — an empty table means it doesn't).
6. Relative links in the `adr/` tier resolve too. Re-tiering moves a document out from
   under every relative link inside it, and `ADR-001` shipped with exactly that break.
7. No file anywhere in the repo cites a RETIRED number without naming where it went. A
   mention is fine as long as the same file also names the successor, which is what
   distinguishes a tombstone, a log row or a footnoted historical record from a surface
   nobody swept. Added after the 2026-07-18 re-tiering left five stale citations behind,
   two of them rendered to readers, with this lint green the whole time.
8. Every doc has a `## Downstream surfaces` section, RATCHETED: docs listed in
   ``LEGACY_NO_DOWNSTREAM`` are grandfathered, and the check fails if a doc *not*
   on that list is missing one. New documents must comply; the list may only
   shrink. This mirrors `SYS-001`'s non-retroactivity clause — fix the rule
   going forward rather than churning what is already cited.

Run locally:
    uv run python scripts/lint_decision_log.py
    python scripts/lint_decision_log.py --list-legacy   # print the grandfathered set
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = REPO_ROOT / "decisions"
ADRS = REPO_ROOT / "adr"
README = REPO_ROOT / "README.md"

# Directories that are generated, vendored or bytecode. The retired-citation sweep walks the
# whole repo, so it has to skip anything it does not own — a stale number inside `portal/` is
# a copy of a source file already being checked, and "fixing" it would be fixing build output.
SKIP_DIRS = {"portal", "site", "graphify-out", "__pycache__", ".git", "node_modules"}
# Text files worth sweeping. Deliberately includes the long tail (.gitignore has no suffix, and
# that is exactly where a stale citation hid) rather than just Markdown.
SWEEP_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".html", ".json", ".toml", ".cjs", ".js", ".css"}
SWEEP_NAMES = {".gitignore", ".gitattributes"}

# Documents predating the mandatory "Downstream surfaces" section. SYS-001's own
# shape list omitted it until 2026-07-18, so an author following the practice
# literally produced a non-compliant document — the fault was the instruction,
# not these docs. Grandfathered rather than backfilled; this list may only shrink.
LEGACY_NO_DOWNSTREAM = {
    "SYS-001", "SYS-002", "SYS-003", "SYS-004", "SYS-005", "SYS-006",
    "SYS-007", "SYS-009", "SYS-010", "SYS-012",
    "SYS-013", "SYS-015",
}
# SYS-008 and SYS-011 left this list on 2026-07-18 by being re-tiered to `adr/ADR-001` and
# `adr/ADR-002` — the sanctioned direction. The list may only shrink.

ROW = re.compile(r"^\|\s*\[(SYS-\d+)\]\(([^)]+)\)\s*\|(.*)\|\s*$")
STATUS = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
MD_LINK = re.compile(r"\[[^\]]*\]\((?!https?://|#)([^)#]+)(?:#[^)]*)?\)")
ALTS = re.compile(r"##\s*Alternatives Considered\s*\n(.*?)(?=\n##\s|\Z)", re.DOTALL)


def _table_rows() -> dict[str, tuple[str, str]]:
    """Parse the README log table into {id: (link_target, status_cell)}."""
    rows: dict[str, tuple[str, str]] = {}
    for line in README.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line.strip())
        if m:
            sys_id, target, rest = m.groups()
            cells = [c.strip() for c in rest.split("|")]
            rows[sys_id] = (target, cells[-1] if cells else "")
    return rows


LIFECYCLE = (
    "superseded", "deprecated", "rejected", "accepted", "proposed", "closed", "moved",
)

# A re-tiered decision leaves a tombstone at its original path so existing citations keep
# resolving (SYS-001's narrowed retroactivity rule). A tombstone is a redirect, not a
# decision, so the content checks below do not apply to it — but it must still carry a row
# in the log table, because a retired number that vanishes from the index is exactly how a
# citation starts coming from memory.
TOMBSTONE_STATUS = "moved"


def _short_status(raw: str) -> str:
    """Extract the lifecycle word from a Status header or table cell.

    Both sides carry decoration the other does not: headers append amendment prose
    ("Accepted — amended 2026-07-18: ..."), and table cells carry emphasis and
    warning markers ("⚠️ **Accepted — BREACHED**"). Comparing first words flags
    every one of those as drift, which would make the check noise — and a check
    that cries wolf gets silenced.

    So match on the lifecycle vocabulary instead. The failure actually being
    guarded is `Proposed` in one place and `Accepted` in the other, which is how
    SYS-009 drifted for three weeks. Ordered longest-lived first so "Superseded by
    ADR-012" does not read as "Accepted".
    """
    lowered = raw.lower()
    for word in LIFECYCLE:
        if word in lowered:
            return word
    return lowered.strip()


def _sweep_files() -> list[Path]:
    """Every first-party text file in the repo, skipping generated and vendored trees."""
    found: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_DIRS & set(path.relative_to(REPO_ROOT).parts):
            continue
        if path.suffix in SWEEP_SUFFIXES or path.name in SWEEP_NAMES:
            found.append(path)
    return sorted(found)


def _retired() -> dict[str, list[str]]:
    """Map each retired SYS id to the markers that prove a citation knows it moved.

    A tombstone's Status line names where the decision went — an `ADR-NNN` for a re-tier
    into `adr/`, or a destination path for a lift into a convention. Either token counts
    as a successor marker.
    """
    retired: dict[str, list[str]] = {}
    for path in sorted(DECISIONS.glob("SYS-*.md")):
        text = path.read_text(encoding="utf-8")
        header = STATUS.search(text)
        if not header or _short_status(header.group(1)) != TOMBSTONE_STATUS:
            continue
        status = header.group(1)
        markers = re.findall(r"ADR-\d+", status)
        markers += [Path(lk).name for lk in MD_LINK.findall(status)]
        retired["-".join(path.name.split("-")[:2])] = markers
    return retired


def check_retired_citations() -> list[str]:
    """Flag files citing a retired SYS number without acknowledging where it went.

    The rule is deliberately loose: a file may cite `SYS-008` freely **as long as the same
    file also names its successor somewhere**. That is what separates a legitimate mention
    — a tombstone, a log-table row, a dated record with a footnote, an "ADR-001, then
    SYS-008" historical form — from a surface that simply never got swept.

    This exists because the 2026-07-18 re-tiering left five stale citations behind, two of
    them rendered to readers (a public portfolio page, and a string emitted into the
    deployed portal). The lint was green throughout: it read `decisions/` and the log table,
    so it verified the log was internally consistent and said nothing about the rest of the
    repo citing it. Same shape as the drift it was written to catch.
    """
    problems: list[str] = []
    retired = _retired()
    if not retired:
        return problems

    for path in _sweep_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for sys_id, markers in retired.items():
            if sys_id not in text:
                continue
            # A tombstone is exempt for its OWN number: its whole job is to carry that number.
            # (Match on the filename prefix, not on `rel == sys_id` — the file is
            # `SYS-011-generated-roadmap-dashboard.md`, not `SYS-011`.)
            if path.name.startswith(sys_id) or any(m and m in text for m in markers):
                continue
            hint = markers[0] if markers else "its successor"
            problems.append(
                f"{rel}: cites retired '{sys_id}' and never names where it went "
                f"(expected a mention of '{hint}' somewhere in the file). Either repoint "
                f"it, or, if the mention is a dated historical record, say so in the "
                f"file so the citation reads as history rather than as current structure."
            )
    return problems


def lint() -> list[str]:
    """Run every check. Returns a list of human-readable problems."""
    problems: list[str] = []
    rows = _table_rows()
    on_disk = sorted(DECISIONS.glob("SYS-*.md"))
    disk_ids = {p.name.split("-")[0] + "-" + p.name.split("-")[1] for p in on_disk}

    for sys_id in sorted(disk_ids - set(rows)):
        problems.append(
            f"{sys_id} exists on disk but has NO ROW in README.md's log table. "
            f"A doc nobody can find in the index gets cited from memory, which is "
            f"how three surfaces ended up citing a wrong SYS number."
        )
    for sys_id in sorted(set(rows) - disk_ids):
        problems.append(f"README.md lists {sys_id} but no such file exists in decisions/.")

    for path in on_disk:
        sys_id = "-".join(path.name.split("-")[:2])
        text = path.read_text(encoding="utf-8")
        rel = f"decisions/{path.name}"

        header = STATUS.search(text)
        if not header:
            problems.append(f"{rel}: no **Status:** header.")
        elif sys_id in rows:
            table_status = _short_status(rows[sys_id][1])
            doc_status = _short_status(header.group(1))
            if table_status != doc_status:
                problems.append(
                    f"{sys_id}: the log table says '{rows[sys_id][1]}' but the "
                    f"document header says '{header.group(1)}'. SYS-009 drifted "
                    f"this way for three weeks."
                )

        if sys_id in rows:
            target = REPO_ROOT / rows[sys_id][0].lstrip("./")
            if not (DECISIONS / Path(rows[sys_id][0]).name).exists() and not target.exists():
                problems.append(f"{sys_id}: table link '{rows[sys_id][0]}' does not resolve.")

        for link in MD_LINK.findall(text):
            if (path.parent / link).resolve().exists():
                continue
            if (REPO_ROOT / link).resolve().exists():
                continue
            problems.append(f"{rel}: relative link '{link}' does not resolve.")

        # A tombstone redirects; it does not decide. Skip the content checks, but only
        # after confirming it actually points somewhere — a redirect to nothing is worse
        # than no redirect, because it looks handled.
        if header and _short_status(header.group(1)) == TOMBSTONE_STATUS:
            # A destination is anything OUTSIDE decisions/ — a repo-local ADR tier
            # (../adr/), a house convention (../engineering/README.md), or another repo.
            # Deliberately not restricted to adr/: SYS-014 was re-tiered to a convention,
            # not to an ADR, and a check that only understood one destination shape would
            # have blocked a correct move. Found by this lint failing on that exact case.
            # NB: str.lstrip("./") strips CHARACTERS, not a prefix — it turns
            # "../adr/x.md" into "adr/x.md" and silently eats the "..". Match the raw
            # link instead. This lint caught its own bug here.
            targets = [lk for lk in MD_LINK.findall(text) if lk.startswith("../")]
            if not targets:
                problems.append(
                    f"{rel}: status is '{TOMBSTONE_STATUS}' but no link to a destination "
                    f"outside decisions/ was found. A tombstone must name where the "
                    f"decision went, or it is just a dead end."
                )
            continue

        alts = ALTS.search(text)
        if not alts or not [
            ln for ln in alts.group(1).splitlines()
            if ln.strip().startswith("|") and not set(ln.strip()) <= set("|- ")
        ][2:]:
            problems.append(
                f"{rel}: 'Alternatives Considered' is missing or has no option rows. "
                f"The promotion bar's second prong is that a decision FORECLOSES "
                f"something; an empty table means it did not."
            )

        if "## Downstream surfaces" not in text and sys_id not in LEGACY_NO_DOWNSTREAM:
            problems.append(
                f"{rel}: missing '## Downstream surfaces'. Mandatory per TEMPLATE.md "
                f"and SYS-009 ('None' is a valid answer but must be written). "
                f"Grandfathered docs are listed in LEGACY_NO_DOWNSTREAM; that list "
                f"may only shrink."
            )

    # The repo-local ADR tier. It gets the link check only — it has no index table to drift
    # against — but that is the check it needed: `ADR-001` shipped with a relative link to
    # `SYS-017-evals-as-ci.md` that resolved from `decisions/`, where the text used to live,
    # and not from `adr/`, where it now does. Re-tiering moves a file out from under every
    # relative link in it, and nothing was checking the destination tier.
    for path in sorted(ADRS.glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8")
        rel = f"adr/{path.name}"
        if not STATUS.search(text):
            problems.append(f"{rel}: no **Status:** header.")
        for link in MD_LINK.findall(text):
            if (path.parent / link).resolve().exists():
                continue
            if (REPO_ROOT / link).resolve().exists():
                continue
            problems.append(f"{rel}: relative link '{link}' does not resolve.")

    problems.extend(check_retired_citations())
    return problems


def main() -> int:
    """Lint the log; exit 1 on any problem."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-legacy", action="store_true", help="Print grandfathered ids.")
    args = parser.parse_args()

    if args.list_legacy:
        print(
            f"{len(LEGACY_NO_DOWNSTREAM)} doc(s) grandfathered out of the "
            f"'Downstream surfaces' rule:"
        )
        for sys_id in sorted(LEGACY_NO_DOWNSTREAM):
            print(f"  {sys_id}")
        return 0

    problems = lint()
    if problems:
        # ASCII only in output: this runs on a Windows console (cp1252) as well as
        # in CI, and a linter that crashes on its own success message is worse
        # than no linter. Found the hard way.
        print("DECISION LOG LINT - problems found:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}\n", file=sys.stderr)
        return 1

    total = len(list(DECISIONS.glob("SYS-*.md")))
    adrs = len(list(ADRS.glob("ADR-*.md")))
    swept = len(_sweep_files())
    print(
        f"OK - decision log clean. {total} SYS + {adrs} ADR documents, table in sync, "
        f"statuses match, links resolve, alternatives present; {swept} files swept for "
        f"retired-number citations."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
