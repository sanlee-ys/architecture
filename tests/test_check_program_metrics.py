"""Failure-path regression tests for the prose-metrics guard.

WHY THESE EXIST. Until now `check_program_metrics.py` was exercised in CI exactly one
way: by being *run* against this repo's real content, where it is expected to pass. That
validates the happy path and nothing else. Every failure branch — the drift detection that
is the entire point of the script — was unexecuted, so the guard could stop guarding and
CI would stay green. That is the same "a check that verifies nothing reads as a pass"
failure the script itself is written to prevent, one level up.

It is not hypothetical. On 2026-07-26, while PR #78 extended the checker to assert the
`sanlee-ys/sanlee-ys` profile README, the first draft asserted per-surface liveness as
"did this surface carry ANY marker". A test that wrapped the remote version marker in
backticks passed clean: three healthy metric markers kept that surface's count nonzero,
and this repo's OWN local version markers kept the global version check satisfied, so the
stripped claim was invisible from both directions. It was caught only by throwaway scripts
in a scratchpad, which were then thrown away. `test_backticked_remote_version_marker_is_caught`
is that scenario, kept.

WHAT IS STUBBED, AND WHY. Both surfaces. `fetch_artifact` and `fetch_text` are module-level
functions precisely so they can be replaced; no test here touches the network, so CI does
not gain a dependency on GitHub being up in order to know whether the guard works.
`REPO_ROOT`/`SCANNED` are pointed at a tmpdir too, rather than reusing the real files: the
version-marker test needs a *healthy local* version marker present at the same time as a
*stripped remote* one, because that co-occurrence is the whole reason the weak check read
as green. Reusing real repo content would also make these tests fail whenever the prose is
legitimately edited, which is the fastest route to a test suite nobody trusts.

These tests pin CURRENT behaviour, which is verified-good as of PR #78. They are not a
specification to design against; if a check is deliberately changed, change the test in the
same commit and say why.
"""

from __future__ import annotations

import pytest

import check_program_metrics as cpm

# The artifact the producer publishes, reduced to what the checker actually reads. Values
# are arbitrary but internally consistent — the point is drift *against* them, not the
# numbers themselves.
ARTIFACT = {
    "version": "3.1.0",
    "gold": {
        "category_accuracy": 92.6,
        "domain_accuracy": 90.1,
        "region_accuracy": 88.0,
        "macro_f1": 0.911,
    },
}

REMOTE_LABEL = "stub-owner/stub-repo:README.md"
REMOTE_URL = "https://raw.githubusercontent.com/stub-owner/stub-repo/main/README.md"

# A healthy local surface. It carries a version marker deliberately: several tests below
# depend on the GLOBAL version check being satisfied so that only the per-surface check can
# possibly catch the injected fault.
LOCAL_CLEAN = """# Local surface

The classifier is at <!-- version:classifier -->**v3.1.0** today.
"""

# A healthy remote surface: 1 version marker + 3 metric markers, matching `expect` below.
REMOTE_CLEAN = """# Profile

Classifier <!-- version:classifier -->**v3.1.0**

- category <!-- metric:category_accuracy -->**92.6%**
- domain <!-- metric:domain_accuracy -->**90.1%**
- region <!-- metric:region_accuracy -->**88.0%**
"""


@pytest.fixture
def configure(monkeypatch):
    """Point the checker at a stubbed artifact, one local file and one remote surface.

    Returns a callable so each test can vary exactly one thing. Defaults are the clean
    state, so every test below reads as "clean, except for the one injected fault" — which
    is what makes a passing assertion evidence that *that* fault was what tripped it.
    """

    def _configure(
        *,
        tmp_path,
        local_text: str = LOCAL_CLEAN,
        remote_text: str | None = REMOTE_CLEAN,
        artifact: dict | None = ARTIFACT,
        expect: dict | None = None,
        unmarked_allowed: dict | None = None,
    ):
        (tmp_path / "local.md").write_text(local_text, encoding="utf-8")
        monkeypatch.setattr(cpm, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(cpm, "SCANNED", ("local.md",))
        monkeypatch.setattr(
            cpm,
            "REMOTE_SCANNED",
            {
                REMOTE_LABEL: {
                    "url": REMOTE_URL,
                    "expect": expect if expect is not None else {"version": 1, "metric": 3},
                }
            },
        )
        monkeypatch.setattr(
            cpm, "UNMARKED_ALLOWED", unmarked_allowed if unmarked_allowed is not None else {}
        )
        monkeypatch.setattr(cpm, "fetch_artifact", lambda url: artifact)
        monkeypatch.setattr(cpm, "fetch_text", lambda url: remote_text)
        # main() parses argv; without this, pytest's own flags reach argparse.
        monkeypatch.setattr("sys.argv", ["check_program_metrics.py"])

    return _configure


def test_clean_state_passes(configure, tmp_path, capsys):
    """The baseline. Without it, every assertion below could be passing for the wrong reason.

    A test suite that only proves a checker fails is satisfied by a checker that always
    fails, which is not a guard — it is an outage.
    """
    configure(tmp_path=tmp_path)
    assert cpm.main() == 0
    out = capsys.readouterr().out
    assert "OK -" in out
    # SYS-019's third property: the check reports its own reach, so a surface it did not
    # actually read cannot be mistaken for one it did.
    assert f"remote surface {REMOTE_LABEL}: checked" in out


def test_version_drift_is_caught(configure, tmp_path):
    """A stale version claim fails.

    The original 2026-07-19 failure: the roadmap advertised the classifier at v2.0.0 while
    v3.0.0 had shipped. A version string is a status claim, not a number, so the metrics
    matcher could not see it.
    """
    configure(tmp_path=tmp_path, remote_text=REMOTE_CLEAN.replace("v3.1.0", "v3.0.0"))
    problems, _, _, _ = cpm.scan()
    assert any("described as v3.0.0" in p and "v3.1.0" in p for p in problems)


def test_metric_drift_is_caught(configure, tmp_path):
    """A marked number that disagrees with the artifact fails. The guard's core job.

    This is the 2026-07-19 failure the script was written for: three narrative surfaces
    quoting v2's 88.9% a day after v3.0.0's 92.6% shipped.
    """
    configure(tmp_path=tmp_path, remote_text=REMOTE_CLEAN.replace("**92.6%**", "**88.9%**"))
    problems, _, _, _ = cpm.scan()
    assert any("'category_accuracy' is written as 88.9%" in p for p in problems)


def test_backticked_remote_version_marker_is_caught(configure, tmp_path):
    """THE important one — the bug found in PR #78's first draft, pinned.

    Wrapping a marked version value in backticks makes the marker match NOTHING: code
    spans are stripped before scanning, so `<!-- version:classifier -->**`v3.1.0`**`
    becomes `<!-- version:classifier -->****`. The claim is still rendered to readers and
    is no longer checked — the worst of both.

    Note what does NOT catch it, which is why this test is worth its length:
      - the surface still carries 3 healthy metric markers, so any "did this surface have
        markers at all" liveness check is satisfied;
      - the LOCAL file still carries a healthy version marker, so the global
        `versions_checked == 0` guard is satisfied too.
    The assertions below check both of those escape routes are genuinely open, and that
    the per-type per-surface count in `REMOTE_SCANNED['expect']` is what closes the door.
    """
    backticked = REMOTE_CLEAN.replace(
        "<!-- version:classifier -->**v3.1.0**",
        "<!-- version:classifier -->**`v3.1.0`**",
    )
    configure(tmp_path=tmp_path, remote_text=backticked)
    problems, marked, _, _ = cpm.scan()

    assert any(
        f"{REMOTE_LABEL}: expected 1 'version' marker(s) but matched 0" in p for p in problems
    )
    # The two escape routes, asserted rather than described: markers were still found
    # overall, and no global "no version marker anywhere" problem was raised.
    assert marked > 0
    assert not any("No <!-- version:classifier --> marker matched" in p for p in problems)


def test_backticked_remote_metric_marker_is_caught(configure, tmp_path):
    """The same stripping trick one field over.

    There is no global liveness guard for metric markers at all, so per-surface counting is
    the only thing standing between a backticked metric claim and a green build.
    """
    backticked = REMOTE_CLEAN.replace(
        "<!-- metric:category_accuracy -->**92.6%**",
        "<!-- metric:category_accuracy -->**`92.6%`**",
    )
    configure(tmp_path=tmp_path, remote_text=backticked)
    problems, _, _, _ = cpm.scan()
    assert any(
        f"{REMOTE_LABEL}: expected 3 'metric' marker(s) but matched 2" in p for p in problems
    )


def test_unknown_metric_key_is_caught(configure, tmp_path):
    """A typo'd key is checked against nothing and would otherwise pass forever."""
    typo = REMOTE_CLEAN.replace("metric:category_accuracy", "metric:categry_accuracy")
    configure(tmp_path=tmp_path, remote_text=typo)
    problems, _, _, _ = cpm.scan()
    assert any("metric key 'categry_accuracy' is not in the artifact" in p for p in problems)


# --- placement: a marker that begins a line -------------------------------------------
#
# The failure these pin is the inverse of the usual one. Drift is loud once someone looks;
# this is silent by construction — the marker is invisible in the SOURCE (so review misses
# it) and stops being invisible on the RENDERED page (so readers get literal `**`). Four
# offences had shipped in this repo before the rule existed, and the checker was green for
# every one of them.
#
# Note that every fixture above places its markers after text on the line. That is load-
# bearing, not incidental: in faithfulness-judge four pre-existing tests had column-zero
# fixtures, which would have documented the broken shape as the correct one.


def test_marker_at_column_zero_is_caught(configure, tmp_path):
    broken = LOCAL_CLEAN.replace(
        "The classifier is at <!-- version:classifier -->**v3.1.0** today.",
        "The classifier is at\n<!-- version:classifier -->**v3.1.0** today.",
    )
    configure(tmp_path=tmp_path, local_text=broken)
    problems, _, _, _ = cpm.scan()
    assert any(
        "local.md:4: a marker is the first thing on this line" in p for p in problems
    )


def test_marker_indented_inside_a_list_item_is_caught(configure, tmp_path):
    """The shape that actually shipped here, and the reason `^<!--` alone is not enough.

    Indented to a list item's content column the marker does not *look* line-initial, but
    an HTML block opens on up to three spaces and the item's content starts at column 2.
    All four offences in `product/one-pager.md` and `case-study/README.md` were this.
    """
    broken = LOCAL_CLEAN + (
        "\n- **Classification quality** — on the n=54 gold set it is\n"
        "  <!-- metric:category_accuracy -->**92.6%** category, which has held.\n"
    )
    configure(tmp_path=tmp_path, local_text=broken)
    problems, _, _, _ = cpm.scan()
    assert any(
        "local.md:6: a marker is the first thing on this line" in p for p in problems
    )


def test_line_initial_marker_is_caught_on_a_remote_surface(configure, tmp_path):
    """Remote surfaces get the same rule — the render they break is a published page."""
    broken = REMOTE_CLEAN.replace(
        "- category <!-- metric:category_accuracy -->**92.6%**",
        "- category\n  <!-- metric:category_accuracy -->**92.6%**",
    )
    configure(tmp_path=tmp_path, remote_text=broken)
    problems, _, _, _ = cpm.scan()
    assert any(
        f"{REMOTE_LABEL}:6: a marker is the first thing on this line" in p
        for p in problems
    )


def test_line_initial_marker_fails_even_when_its_value_is_correct(configure, tmp_path):
    """Placement is the defect. A value that matches the artifact does not excuse it.

    This is what makes the rule necessary rather than redundant: every one of the four
    offences in this repo carried a perfectly correct number.
    """
    broken = LOCAL_CLEAN.replace(
        "The classifier is at <!-- version:classifier -->**v3.1.0** today.",
        "The classifier is at\n<!-- version:classifier -->**v3.1.0** today.",
    )
    configure(tmp_path=tmp_path, local_text=broken)
    problems, _, _, _ = cpm.scan()
    assert not any("described as v" in p for p in problems), "the value is correct"
    assert any("first thing on this line" in p for p in problems)


def test_line_initial_marker_inside_a_fence_is_documentation_not_a_use(configure, tmp_path):
    """`engineering/README.md` documents this convention; documenting it must not invoke it.

    The example there is a one-liner today, but the natural way to show a *placement* rule
    is a fenced block with the bad shape in it, so this has to be safe.
    """
    documented = LOCAL_CLEAN + (
        "\nNever write it like this:\n\n"
        "```markdown\n"
        "category accuracy\n"
        "<!-- metric:category_accuracy -->92.6%\n"
        "```\n"
    )
    configure(tmp_path=tmp_path, local_text=documented)
    problems, _, _, _ = cpm.scan()
    assert not any("first thing on this line" in p for p in problems)


def test_line_number_is_the_editors_line_number(configure, tmp_path):
    """Reported lines are computed on the RAW text, not the code-stripped copy.

    `scan()` deletes fenced blocks before matching. If the placement rule ran on that copy,
    every line after a fence would be reported short by the height of the fence, and the
    directed message would point a reader at the wrong line — which is worse than no line
    number, because it looks authoritative.
    """
    with_fence = (
        LOCAL_CLEAN
        + "\n```python\nx = 1\ny = 2\nz = 3\n```\n\nCurrent figures:\n"
        + "<!-- metric:category_accuracy -->**92.6%**\n"
    )
    configure(tmp_path=tmp_path, local_text=with_fence)
    problems, _, _, _ = cpm.scan()
    offence = next(p for p in problems if "first thing on this line" in p)
    # The marker is on line 12 of the file as written; the fence is 5 lines of it.
    assert with_fence.splitlines()[11].startswith("<!-- metric:")
    assert "local.md:12:" in offence


# --- placement is swept over EVERY markdown file; the value rules are not -------------
#
# `SCANNED` is narrow on purpose and stays narrow: its rules ask "is this number still
# current?", which is meaningless for `decisions/` and `adr/`, where an ADR is a dated
# record. Placement asks "does this file render?" — true of every file — so it alone is
# swept over the tree. The fixtures below keep the same discipline as the section above:
# a marker sits after text unless line-initial placement is the thing under test.


def test_the_sweep_reaches_files_scanned_does_not(configure, tmp_path):
    configure(tmp_path=tmp_path)
    (tmp_path / "decisions").mkdir()
    (tmp_path / "decisions" / "SYS-999.md").write_text("dated record\n", encoding="utf-8")
    swept = {p.relative_to(tmp_path).as_posix() for p in cpm.sweep_paths(tmp_path, cpm.SCANNED)}
    assert "decisions/SYS-999.md" in swept
    # ...and not what SCANNED already owns, or a bad marker would be reported twice.
    assert "local.md" not in swept


def test_line_initial_marker_outside_scanned_is_caught(configure, tmp_path):
    """The gap this closes: `decisions/` could break its own page with nothing to notice."""
    configure(tmp_path=tmp_path)
    (tmp_path / "adr").mkdir()
    (tmp_path / "adr" / "ADR-999.md").write_text(
        "The classifier is at\n<!-- version:classifier -->**v3.1.0** today.\n",
        encoding="utf-8",
    )
    problems = cpm.check_placement(tmp_path, cpm.sweep_paths(tmp_path, cpm.SCANNED))
    assert any("adr/ADR-999.md:2: a marker is the first thing" in p for p in problems)


def test_fenced_marker_outside_scanned_passes(configure, tmp_path):
    """Same file, same column-zero marker, only the fence differs."""
    configure(tmp_path=tmp_path)
    (tmp_path / "adr").mkdir()
    (tmp_path / "adr" / "ADR-999.md").write_text(
        "Never write it like this:\n\n```markdown\n"
        "<!-- metric:category_accuracy -->92.6%\n```\n",
        encoding="utf-8",
    )
    assert cpm.check_placement(tmp_path, cpm.sweep_paths(tmp_path, cpm.SCANNED)) == []


def test_the_sweep_applies_only_the_placement_rule(configure, tmp_path):
    """A stale value or unknown key in an ADR is NOT a failure — that is the whole split.

    If this ever starts failing, the value rules have leaked into `decisions/`, and the
    next person to "fix" it will do so by re-syncing a dated record to today's numbers.
    """
    configure(tmp_path=tmp_path)
    (tmp_path / "decisions").mkdir()
    (tmp_path / "decisions" / "SYS-999.md").write_text(
        "In June it measured <!-- metric:category_accuracy -->**88.9%**, "
        "and <!-- metric:typo_key -->**79.0%** on the synthetic set.\n",
        encoding="utf-8",
    )
    assert cpm.check_placement(tmp_path, cpm.sweep_paths(tmp_path, cpm.SCANNED)) == []


def test_the_sweep_does_not_walk_generated_or_vendored_trees(configure, tmp_path):
    """`portal/` is build output; editing a marker there fixes a copy, not a source."""
    configure(tmp_path=tmp_path)
    for skipped in ("portal", "site", ".claude", "node_modules", "__pycache__"):
        (tmp_path / skipped).mkdir()
        (tmp_path / skipped / "STRAY.md").write_text(
            "generated\n<!-- metric:category_accuracy -->**92.6%**\n", encoding="utf-8"
        )
    assert cpm.sweep_paths(tmp_path, cpm.SCANNED) == []


def test_placement_still_runs_when_the_artifact_fetch_fails(configure, tmp_path, capsys):
    """An outage skips the value rules. It must not skip a rule that needs no artifact.

    Otherwise a bad merge lands green during a GitHub blip — a gate that did not
    actually run, which this repo counts as a failure rather than a pass.
    """
    configure(tmp_path=tmp_path, artifact=None)
    (tmp_path / "adr").mkdir()
    (tmp_path / "adr" / "ADR-999.md").write_text(
        "The classifier is at\n<!-- version:classifier -->**v3.1.0** today.\n",
        encoding="utf-8",
    )
    assert cpm.main() == 1
    assert "first thing on this line" in capsys.readouterr().err


def test_a_clean_tree_still_passes_when_the_artifact_fetch_fails(configure, tmp_path, capsys):
    """The other half: an outage with no placement fault is still a loud skip, not a fail."""
    configure(tmp_path=tmp_path, artifact=None)
    assert cpm.main() == 0
    assert "SKIPPED" in capsys.readouterr().out


def test_unmarked_number_over_allowance_is_caught(configure, tmp_path):
    """The coverage ratchet: a NEW metric-shaped number nobody marked fails the build.

    Marking is opt-in, so without this the guard only ever covers what an author
    remembered — the same trust-the-author model that failed in the first place.
    """
    configure(tmp_path=tmp_path, local_text=LOCAL_CLEAN + "\nAccuracy is now 99.9% here.\n")
    problems, _, unmarked, _ = cpm.scan()
    assert unmarked["local.md"] == ["99.9%"]
    assert any("local.md: 1 unmarked metric-shaped number(s) but only 0 allowed" in p
               for p in problems)


def test_unmarked_number_within_allowance_passes(configure, tmp_path):
    """The other half of the ratchet: a grandfathered historical figure must NOT fail.

    Historical figures are deliberately unmarked — marking them would make the guard
    rewrite history on every release. If the allowance stopped working, the pressure would
    be to mark them, which is the failure this half prevents.
    """
    configure(
        tmp_path=tmp_path,
        local_text=LOCAL_CLEAN + "\nThe v1 synthetic baseline was 79.4%.\n",
        unmarked_allowed={"local.md": 1},
    )
    problems, _, _, _ = cpm.scan()
    assert problems == []


def test_artifact_fetch_failure_warns_and_passes(configure, tmp_path, capsys):
    """A GitHub outage must not redden an unrelated build.

    Bounded deliberately: this is the ONE branch where "cannot tell" is allowed to read as
    a pass, because the alternative is a guard people switch off. Everything else that
    looks like "no markers found" fails.
    """
    configure(tmp_path=tmp_path, artifact=None)
    assert cpm.main() == 0
    assert "SKIPPED" in capsys.readouterr().out


def test_remote_fetch_failure_warns_passes_and_reports_skipped(configure, tmp_path, capsys):
    """Same bound for a remote surface — and it must SAY it was skipped.

    Passing quietly here would make an unreachable surface indistinguishable from a
    verified one, which is exactly the "narrower than its claim surface" failure SYS-019
    names.
    """
    configure(tmp_path=tmp_path, remote_text=None)
    assert cpm.main() == 0
    out = capsys.readouterr().out
    assert f"remote surface {REMOTE_LABEL}: SKIPPED (fetch failed)" in out


def test_fetched_but_empty_remote_surface_fails(configure, tmp_path):
    """A fetched-but-empty surface FAILS, unlike an unfetchable one.

    Both look like "no markers found". Collapsing them would let a silent 404 body, an
    emptied file, or a wholesale rewrite read exactly like a healthy check — which is why
    the script tracks *fetched* separately from *has markers*.
    """
    configure(tmp_path=tmp_path, remote_text="# Profile\n\nNothing to see here.\n")
    problems, _, _, _ = cpm.scan()
    assert any(f"{REMOTE_LABEL}: expected 1 'version' marker(s) but matched 0" in p
               for p in problems)
    assert any(f"{REMOTE_LABEL}: expected 3 'metric' marker(s) but matched 0" in p
               for p in problems)
