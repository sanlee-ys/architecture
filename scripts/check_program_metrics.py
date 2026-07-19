"""Assert the metrics quoted in this repo's prose against the producer's artifact.

WHY THIS EXISTS. On 2026-07-19 three narrative surfaces here were found quoting the
classifier's **v2** numbers (88.9% / macro-F1 0.906) while the shipped classifier had
been at v3.0.0 (92.6% / 0.911) since the previous day: `program/README.md`'s risk R2,
`product/one-pager.md`, and `case-study/README.md`. Two of the three were found only
because someone happened to grep for a decimal.

The portfolio already had a guard for exactly this failure — `check-published-metrics.cjs`
— but it reads `data-metric` spans in HTML, so it could not see a number written in a
Markdown sentence in a different repo. The gap was not that the rule was unknown. It was
that the rule had no reach here.

HOW A NUMBER OPTS IN. Put an HTML comment immediately before it:

    category <!-- metric:category_accuracy -->**92.6%**

The comment is invisible in rendered Markdown and on the generated portal. The key must
exist in the artifact's ``gold`` object; a typo fails rather than silently checking
nothing.

WHAT IS DELIBERATELY NOT MARKED. Historical figures ("the v1 synthetic baseline was
~79%") are frozen records of past runs and must NOT track the latest artifact — marking
them would make the guard rewrite history on every release. That is the same reasoning
that left the graphify eval's output verbatim under `SYS-001`'s narrowed retroactivity
rule.

WHICH FILES ARE SCANNED, AND WHY NOT ALL OF THEM. Only the narrative surfaces: they make
claims in the present tense about how the system performs *now*. `decisions/` and `adr/`
are excluded by design — an ADR is a **dated record** of what was true when it was
written, and `SYS-009`'s guarantee-vs-observation rule says such a document should not be
re-synced to today's numbers. Scanning them would generate pressure to do exactly that.

THE COVERAGE RATCHET. Marking numbers only guards the ones somebody remembered to mark,
which is the same trust-the-author model that failed here. So the scan also counts
metric-shaped numbers that are NOT marked, per file, against ``UNMARKED_ALLOWED``. Exceed
the allowance and the check fails. The allowance may only shrink. This is the same shape
as ``LEGACY_NO_DOWNSTREAM`` in the decision-log lint: grandfather what exists, make new
drift impossible.

FAILURE POLICY (matches `SYS-018` and the portfolio check):
  - marked value mismatches artifact -> exit 1. The real guard.
  - unknown metric key               -> exit 1. A typo checks nothing and passes forever.
  - unmarked count over allowance    -> exit 1. New unguarded numbers do not get in.
  - zero marked figures              -> exit 1. A check verifying nothing reads as a pass.
  - artifact fetch failure           -> exit 0, loudly. A GitHub outage must not redden an
                                        unrelated build.

Run locally:
    uv run python scripts/check_program_metrics.py
    uv run python scripts/check_program_metrics.py --list-unmarked   # show what is unguarded
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_URL = (
    "https://raw.githubusercontent.com/sanlee-ys/defense-news-classifier/main/evals/metrics.json"
)

# Narrative surfaces: present-tense claims about current performance. Dated records
# (decisions/, adr/) are excluded on purpose — see the module docstring.
SCANNED = (
    "README.md",
    "program/README.md",
    "product/one-pager.md",
    "engineering/README.md",
    "case-study/README.md",
)

# Metric-shaped numbers that are NOT behind a marker, per file. Every one of these is a
# historical figure (a v1 synthetic baseline, a superseded measurement quoted as history)
# that must not track the artifact. The count is the ratchet: it may only shrink. Adding a
# new unmarked number to one of these files fails the build, which is the point.
UNMARKED_ALLOWED = {
    # v1 synthetic-baseline domain accuracy, quoted as history. (The "~79%" category
    # figure alongside it is not counted here: it carries no decimal, so METRIC_SHAPED
    # does not match it. That is a deliberate limit of the pattern, not an oversight -
    # widening it to bare integers would flag every count, date and version in the file.)
    "product/one-pager.md": 1,
    "case-study/README.md": 0,
    "program/README.md": 0,
    "engineering/README.md": 0,
    "README.md": 0,
}

# A percentage to one decimal (92.6%) or a three-decimal F1 (0.911). Deliberately narrow:
# broad number-matching would flag dates, counts and version strings, and a check that
# cries wolf gets silenced.
METRIC_SHAPED = re.compile(r"\b\d{1,3}\.\d%|\b0\.\d{3}\b")
# The value pattern is anchored and precise rather than a loose ``[0-9.]+``: a greedy
# character class swallows the sentence's trailing period, turning "0.927." into a value
# that matches nothing and reports drift against itself. Found by this check failing on
# its own first run.
MARKER = re.compile(r"<!--\s*metric:([A-Za-z0-9_]+)\s*-->\s*\**\s*(\d+(?:\.\d+)?%?)")


def fetch_artifact(url: str) -> dict | None:
    """Fetch the published metrics artifact, or None if it cannot be read."""
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310 - fixed https URL
            if resp.status != 200:
                print(f"WARNING: HTTP {resp.status} fetching the metrics artifact.")
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"WARNING: could not fetch the metrics artifact: {exc}")
        return None


def same_value(shown: str, published: object) -> bool:
    """Compare numerically, not as strings.

    JSON serialises 87.0 as ``87``, so a string compare against the prose's "87.0%"
    reports a mismatch that is not one. Both sides are already rounded at generation, so
    an exact compare is right; the epsilon only absorbs float representation.
    """
    try:
        return abs(float(shown.rstrip("%")) - float(str(published))) < 1e-9
    except ValueError:
        return shown.strip() == str(published).strip()


def scan() -> tuple[list[str], int, dict[str, list[str]]]:
    """Check every scanned file. Returns (problems, marked_count, unmarked_by_file)."""
    artifact = fetch_artifact(ARTIFACT_URL)
    if artifact is None:
        return ([], -1, {})

    published = artifact.get("gold", {})
    known = set(published)
    problems: list[str] = []
    marked = 0
    unmarked: dict[str, list[str]] = {}

    for rel in SCANNED:
        path = REPO_ROOT / rel
        if not path.exists():
            problems.append(f"{rel}: listed in SCANNED but not on disk.")
            continue
        text = path.read_text(encoding="utf-8")

        for key, shown in MARKER.findall(text):
            if key not in known:
                problems.append(
                    f"{rel}: metric key '{key}' is not in the artifact. "
                    f"Known keys: {', '.join(sorted(known))}. A typo'd key is checked "
                    f"against nothing and would pass forever, so this fails."
                )
                continue
            marked += 1
            if not same_value(shown, published[key]):
                problems.append(
                    f"{rel}: '{key}' is written as {shown} but the classifier measured "
                    f"{published[key]}. The artifact is the source of truth - update the "
                    f"prose, not the artifact."
                )

        # Everything metric-shaped that a marker did not claim. Delete the marked spans
        # from the text and scan the remainder, rather than filtering by value: the same
        # figure legitimately appears twice (category and domain are both 92.6%), and a
        # value-set filter would let an UNmarked duplicate hide behind a marked one.
        loose = METRIC_SHAPED.findall(MARKER.sub("", text))
        if loose:
            unmarked[rel] = loose
        allowed = UNMARKED_ALLOWED.get(rel, 0)
        if len(loose) > allowed:
            problems.append(
                f"{rel}: {len(loose)} unmarked metric-shaped number(s) but only {allowed} "
                f"allowed: {', '.join(loose)}. Either mark it "
                f"(<!-- metric:KEY -->) so it is checked, or - if it is a historical "
                f"figure that must not track the artifact - raise the allowance in "
                f"UNMARKED_ALLOWED and say why in the comment there."
            )

    return problems, marked, unmarked


def main() -> int:
    """Run the check; exit 1 on any problem."""
    parser = argparse.ArgumentParser(description="Check prose metrics against the artifact.")
    parser.add_argument(
        "--list-unmarked", action="store_true", help="Print unguarded metric-shaped numbers."
    )
    args = parser.parse_args()

    problems, marked, unmarked = scan()

    if marked == -1:
        print("Prose metrics check SKIPPED (see warning above).")
        return 0

    if args.list_unmarked:
        if not unmarked:
            print("No unmarked metric-shaped numbers in the scanned files.")
            return 0
        print("Unmarked metric-shaped numbers (historical figures, not checked):")
        for rel, nums in sorted(unmarked.items()):
            print(f"  {rel}: {', '.join(nums)}")
        return 0

    if problems:
        print("PROSE METRICS ARE STALE OR UNGUARDED:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}\n", file=sys.stderr)
        print(f"Artifact: {ARTIFACT_URL}", file=sys.stderr)
        return 1

    if marked == 0:
        print(
            "No metric markers found. Either they were dropped or this check is inert - "
            "both are failures, because a check that verifies nothing reads as a pass.",
            file=sys.stderr,
        )
        return 1

    total_unmarked = sum(len(v) for v in unmarked.values())
    print(
        f"OK - {marked} prose metric(s) match the classifier artifact. "
        f"{total_unmarked} historical figure(s) deliberately unguarded "
        f"(--list-unmarked to see them)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
