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

SURFACES IN OTHER REPOS. `REMOTE_SCANNED` fetches a published file over HTTPS and scans
it with the identical logic. Added 2026-07-26 for the GitHub profile README
(`sanlee-ys/sanlee-ys`), which was found advertising the classifier at v3.0.0 the day
after v3.1.0 shipped — caught by a person reading it.

That repo could have grown its own checker instead. It was declined on two grounds: it
would have been that repo's FIRST workflow (dragging in a Dependabot block and a Python
toolchain for one script in a six-file repo), and it would have been `SYS-019`'s FIFTH
checker — the exact count that ADR names as its own revisit trigger, where "the
duplication argument flips" toward a shared package. Reaching one more surface from the
checker that already exists is the smaller move.

The accepted cost is that this is **detection, not prevention**: a bad edit to a remote
surface merges green in its own repo and reddens *this* build afterward. Remote surfaces
are read from the published ref, so what is asserted is what the public currently sees —
which is the right question to ask about an outward claim, just answered late.

WHY A FETCH FAILURE AND AN EMPTY FETCH ARE TREATED DIFFERENTLY. A remote surface that
cannot be fetched warns and passes, per the policy below. A remote surface that IS
fetched but does not carry the marker counts declared in `REMOTE_SCANNED` FAILS. Both can
look like "no markers found," and collapsing them would let a silent 404 body, an empty
file, or a marker someone deleted read exactly like a healthy check.

Liveness for remote surfaces is asserted per surface AND per marker type, which is
stricter than the global version check below and had to be. Sixteen healthy markers once
masked a marker type that matched nothing at all; the same aggregation defeats a
per-surface count the moment there is more than one surface, because a stripped marker on
one hides behind healthy markers on another. An aggregate liveness count is only as
strong as its narrowest partition.

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
  - remote marker count off          -> exit 1. Asserted per surface AND per marker type;
                                        a stripped or backticked marker otherwise hides
                                        behind its healthy neighbours.
  - artifact fetch failure           -> exit 0, loudly. A GitHub outage must not redden an
                                        unrelated build.
  - remote surface fetch failure     -> exit 0, loudly; that surface is skipped. Same
                                        bound as the artifact fetch.

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

# Narrative surfaces in OTHER repos, fetched from their published ref. The label is what
# appears in error messages; it is prefixed so a failure is obviously not a local file.
#
# `expect` is the EXACT number of markers of each type the surface should carry, and it is
# a hard assertion, not documentation. A bare "did this surface have any markers at all"
# check is not enough, and that is not a hypothetical: it was written that way first and a
# test that backticked the remote version marker passed clean, because three healthy
# metric markers kept the surface's count nonzero and this repo's OWN local version
# markers kept the global version check satisfied. The stripped claim was invisible from
# both directions. Counting per type per surface is what closes it.
#
# Exact rather than minimum, deliberately: if a blurb gains or loses a marked claim, this
# inventory must be updated in the same change, so the file stays an accurate statement of
# what is actually guarded over there rather than drifting into an optimistic guess.
REMOTE_SCANNED = {
    "sanlee-ys/sanlee-ys:README.md": {
        "url": "https://raw.githubusercontent.com/sanlee-ys/sanlee-ys/main/README.md",
        # 1 classifier version + category/domain/region accuracy.
        "expect": {"version": 1, "metric": 3},
    },
}

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
    # The two v2.1.0 SCALED-eval accuracies (93.3% category, 90.3% domain, n=300 judge-
    # graded). They are real measurements but they are not in this artifact, which
    # publishes the n=54 human gold set only - marking them against it would assert a
    # number against the wrong measurement, which is worse than leaving them unchecked.
    # They belong to `evals/scale_eval.txt`; if that is ever published as an artifact
    # too, this allowance should drop back to 0.
    "program/README.md": 2,
    "engineering/README.md": 0,
    "README.md": 0,
    # The profile README's kb-agent figures (recall@5 0.926, MRR 0.781) and
    # faithfulness-judge figures (Opus kappa 0.751, Sonnet 0.716). These are real, current
    # measurements - but NEITHER repo publishes a machine-readable artifact to assert them
    # against: kb-agent's live in its README prose, the judge's in `evals/results.md`. So
    # there is no artifact to mark them to, and marking them to THIS one would assert them
    # against the wrong measurement entirely.
    #
    # Stated plainly, because a guard that is quiet about its own scope is how the
    # portfolio check sat green while narrower than its claim surface (SYS-019's last
    # alternative row): this check covers the classifier's four claims on that page and
    # NOT these four. Half that surface remains a human sweep. If either repo publishes an
    # artifact, mark them and drop this allowance.
    "sanlee-ys/sanlee-ys:README.md": 4,
}

# Fenced blocks and inline code spans. Stripped before any scanning: a marker written
# inside backticks is DOCUMENTATION OF the convention, not a use of it, and a figure in a
# code sample is a sample. Found immediately - writing the convention down in
# engineering/README.md made this checker fail on the very page that defines it, reporting
# the literal placeholder `KEY` as an unknown metric key.
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)

# A percentage to one decimal (92.6%) or a three-decimal F1 (0.911). Deliberately narrow:
# broad number-matching would flag dates, counts and version strings, and a check that
# cries wolf gets silenced.
METRIC_SHAPED = re.compile(r"\b\d{1,3}\.\d%|\b0\.\d{3}\b")
# The value pattern is anchored and precise rather than a loose ``[0-9.]+``: a greedy
# character class swallows the sentence's trailing period, turning "0.927." into a value
# that matches nothing and reports drift against itself. Found by this check failing on
# its own first run.
MARKER = re.compile(r"<!--\s*metric:([A-Za-z0-9_]+)\s*-->\s*\**\s*(\d+(?:\.\d+)?%?)")

# Version claims, same idea one field over: `<!-- version:classifier -->**`v3.0.0`**`
# asserts against the artifact's own `version`. Added 2026-07-19 after the roadmap was
# found advertising the classifier at v2.0.0 (it was v3.0.0) and listing an already-shipped
# v2.1.0 under "Next". The metrics guard could not see either: it checks NUMBERS, and a
# version string is a status claim. Same failure class, different field - so it gets the
# same treatment rather than a promise to be careful.
# NB: do NOT wrap a marked version in backticks in the prose. Code spans are stripped
# before scanning (see CODE above), so `v3.0.0` would be removed and this marker would
# match nothing — a check that silently verifies nothing. That happened on this very
# change: the first draft used **`v3.0.0`** and reported OK against injected drift.
# The zero-marker guard in main() now makes that failure loud instead of invisible.
VERSION_MARKER = re.compile(r"<!--\s*version:classifier\s*-->\s*\**\s*v?(\d+\.\d+\.\d+)")


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


def fetch_text(url: str) -> str | None:
    """Fetch a remote surface's raw text, or None if it cannot be read.

    NB: raw.githubusercontent.com serves ``Cache-Control: max-age=300``, and a
    ``no-cache`` request header does not bypass it (measured, not assumed). So for up to
    five minutes after a remote surface is edited, this reads the previous content.

    Left alone deliberately. The window is bounded, it self-corrects on the next run, and
    both directions of error are transient: a fix that has just landed can read as a
    stale red, and drift that has just landed can read as a green. Neither persists. The
    alternative - authenticating against the contents API to dodge one CDN's TTL - buys a
    five-minute improvement in exchange for a token and an auth failure mode, on a check
    whose whole job is to be boring enough that nobody switches it off.
    """
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310 - fixed https URL
            if resp.status != 200:
                print(f"WARNING: HTTP {resp.status} fetching {url}.")
                return None
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"WARNING: could not fetch {url}: {exc}")
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


def scan() -> tuple[list[str], int, dict[str, list[str]], set[str]]:
    """Check every scanned surface.

    Returns (problems, marked_count, unmarked_by_file, remote_surfaces_fetched). The last
    is reported by main() so a skipped remote surface is visible in the log rather than
    being indistinguishable from a clean pass.
    """
    artifact = fetch_artifact(ARTIFACT_URL)
    if artifact is None:
        return ([], -1, {}, set())

    published = artifact.get("gold", {})
    known = set(published)
    artifact_version = str(artifact.get("version", ""))
    problems: list[str] = []
    marked = 0
    versions_checked = 0
    unmarked: dict[str, list[str]] = {}

    # Local files first, then remote surfaces. A remote surface that cannot be fetched is
    # dropped from the work list with a warning rather than failing - a GitHub outage must
    # not redden this build. One that IS fetched is held to the same bar as a local file,
    # plus a liveness assertion below: see the module docstring on why those two cases are
    # deliberately not collapsed.
    surfaces: list[tuple[str, str]] = []

    for rel in SCANNED:
        path = REPO_ROOT / rel
        if not path.exists():
            problems.append(f"{rel}: listed in SCANNED but not on disk.")
            continue
        surfaces.append((rel, path.read_text(encoding="utf-8")))

    remote_fetched: set[str] = set()
    for label, spec in REMOTE_SCANNED.items():
        body = fetch_text(spec["url"])
        if body is None:
            print(f"WARNING: skipping remote surface {label} (see above).")
            continue
        remote_fetched.add(label)
        surfaces.append((label, body))

    for rel, raw in surfaces:
        # Code spans hold examples, not claims. Strip them before anything else so the
        # page documenting the convention is not read as using it.
        text = CODE.sub("", raw)
        seen_here = {"version": 0, "metric": 0}

        for shown in VERSION_MARKER.findall(text):
            marked += 1
            seen_here["version"] += 1
            versions_checked += 1
            if shown != artifact_version:
                problems.append(
                    f"{rel}: the classifier is described as v{shown} but the published "
                    f"artifact is v{artifact_version}. A version claim goes stale the "
                    f"same way a number does, and reads as current the same way."
                )

        for key, shown in MARKER.findall(text):
            if key not in known:
                problems.append(
                    f"{rel}: metric key '{key}' is not in the artifact. "
                    f"Known keys: {', '.join(sorted(known))}. A typo'd key is checked "
                    f"against nothing and would pass forever, so this fails."
                )
                continue
            marked += 1
            seen_here["metric"] += 1
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

        # Per-type, per-surface liveness for remote surfaces. A local file that loses a
        # marker shows it in the diff that removed it; a remote one does not - it is edited
        # in another repo, by a PR this build never sees. Counting each type separately is
        # what catches a single stripped or backticked marker hiding behind its healthy
        # neighbours; see the note on `expect` in REMOTE_SCANNED for the test that caught
        # the weaker version of this check.
        if rel in remote_fetched:
            for kind, want in REMOTE_SCANNED[rel]["expect"].items():
                got = seen_here[kind]
                if got != want:
                    problems.append(
                        f"{rel}: expected {want} '{kind}' marker(s) but matched {got}. "
                        f"A marker can go missing three ways, and all three read as a "
                        f"pass without this check: it was deleted (they are invisible in "
                        f"rendered Markdown, so this is the ordinary way to lose one), "
                        f"its value was wrapped in backticks (code spans are stripped "
                        f"before scanning, so it matches nothing), or the surface was "
                        f"rewritten and the claim is simply gone. If the claim was "
                        f"removed or added on purpose, update 'expect' for this surface "
                        f"in REMOTE_SCANNED in the same change."
                    )

    # Per-marker-type liveness. The overall "zero markers" guard in main() is not enough:
    # 16 healthy metric markers happily masked a version check that matched nothing at all
    # because its example was written inside backticks. A marker TYPE that verifies nothing
    # reads as coverage exactly as loudly as one that works.
    if versions_checked == 0:
        problems.append(
            "No <!-- version:classifier --> marker matched in any scanned file. Either "
            "the marker was dropped, or it is wrapped in backticks (code spans are "
            "stripped before scanning, so the marker never matches). Both are failures: "
            "this check would silently verify nothing."
        )

    return problems, marked, unmarked, remote_fetched


def main() -> int:
    """Run the check; exit 1 on any problem."""
    parser = argparse.ArgumentParser(description="Check prose metrics against the artifact.")
    parser.add_argument(
        "--list-unmarked", action="store_true", help="Print unguarded metric-shaped numbers."
    )
    args = parser.parse_args()

    problems, marked, unmarked, remote_surfaces_seen = scan()

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
        f"{total_unmarked} historical or un-artifacted figure(s) deliberately unguarded "
        f"(--list-unmarked to see them)."
    )
    # Say what was reached and what was not. SYS-019's third property: a check that does
    # not report its own scope is how a guard narrower than its claim surface reads as
    # full coverage.
    for label in REMOTE_SCANNED:
        state = "checked" if label in remote_surfaces_seen else "SKIPPED (fetch failed)"
        print(f"  remote surface {label}: {state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
