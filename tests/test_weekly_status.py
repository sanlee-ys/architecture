"""Failure-path and harvest tests for weekly_status.py.

WHAT IS STUBBED. ``run_gh``. Every test injects JSON. No test calls the
network. These tests pin current behaviour. If the harvest rule changes,
change the test in the same commit and say why.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

import weekly_status as ws

DAY = date(2026, 9, 9)
START = date(2026, 9, 2)


def _pr(
    number: int,
    title: str,
    merged_at: str,
    repo: str,
    login: str = "sanlee-ys",
) -> dict:
    return {
        "number": number,
        "title": title,
        "url": f"https://github.com/{repo}/pull/{number}",
        "mergedAt": merged_at,
        "author": {"login": login},
    }


INSIDE = _pr(
    112,
    "test: record live tool-seam gold-set run",
    "2026-09-09T14:42:58Z",
    "sanlee-ys/kb-agent",
)
ALSO_INSIDE = _pr(
    57,
    "docs: cut the README to an operator front door",
    "2026-09-02T13:58:09Z",
    "sanlee-ys/notes-api",
)
OUTSIDE = _pr(
    50,
    "docs: include region in enrichment tag list",
    "2026-08-10T19:00:44Z",
    "sanlee-ys/notes-api",
)


class GhStub:
    """Return canned JSON per ``--repo``. Record the argument lists."""

    def __init__(self, payload: dict[str, list[dict]]):
        self.payload = payload
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> str:
        self.calls.append(list(args))
        repo = args[args.index("--repo") + 1]
        return json.dumps(self.payload.get(repo, []))


@pytest.fixture
def empty_gh():
    return GhStub({repo: [] for repo in ws.REPOS})


def test_empty_week_still_writes_a_file(tmp_path, empty_gh):
    """An empty week is not a skip. The file proves the check ran."""
    path = ws.harvest(DAY, tmp_path, run=empty_gh)
    assert path == tmp_path / "2026-09-09.md"
    text = path.read_text(encoding="utf-8")
    assert "Zero merged PRs" in text
    assert "Merged pull requests: 0" in text
    assert "2026-09-02 through 2026-09-09" in text
    for repo in ws.REPOS:
        assert repo in text


def test_filename_is_the_run_day(tmp_path, empty_gh):
    path = ws.harvest(DAY, tmp_path, run=empty_gh)
    assert path.name == "2026-09-09.md"


def test_window_is_seven_days_inclusive():
    assert ws.window_start(DAY) == START


def test_merged_prs_in_window_are_listed(tmp_path):
    stub = GhStub(
        {
            "sanlee-ys/kb-agent": [INSIDE],
            "sanlee-ys/notes-api": [ALSO_INSIDE, OUTSIDE],
            "sanlee-ys/defense-news-classifier": [],
            "sanlee-ys/architecture": [],
        }
    )
    text = ws.harvest(DAY, tmp_path, run=stub).read_text(encoding="utf-8")
    assert "Merged pull requests: 2" in text
    assert "#112" in text
    assert "test: record live tool-seam gold-set run" in text
    assert "docs: cut the README to an operator front door" in text
    assert "include region in enrichment tag list" not in text
    assert "Zero merged pull requests." in text


def test_open_or_unmerged_rows_are_dropped(tmp_path):
    """A stub row with no mergedAt must not appear. Harvest merged PRs only."""
    open_row = {
        "number": 1,
        "title": "WIP: not merged",
        "url": "https://github.com/sanlee-ys/architecture/pull/1",
        "mergedAt": None,
        "author": {"login": "sanlee-ys"},
    }
    stub = GhStub(
        {
            "sanlee-ys/architecture": [open_row],
            "sanlee-ys/kb-agent": [],
            "sanlee-ys/notes-api": [],
            "sanlee-ys/defense-news-classifier": [],
        }
    )
    text = ws.harvest(DAY, tmp_path, run=stub).read_text(encoding="utf-8")
    assert "WIP: not merged" not in text
    assert "Merged pull requests: 0" in text


def test_gh_is_called_with_state_merged(tmp_path, empty_gh):
    ws.harvest(DAY, tmp_path, run=empty_gh)
    assert empty_gh.calls, "expected one gh call per repo"
    for args in empty_gh.calls:
        assert args[:2] == ["pr", "list"]
        assert "--state" in args
        assert args[args.index("--state") + 1] == "merged"
        assert "--json" in args


def test_invalid_json_exits(tmp_path):
    def bad(_args):
        return "not-json{"

    with pytest.raises(SystemExit) as exc:
        ws.list_merged_prs("sanlee-ys/architecture", START, DAY, run=bad)
    assert "invalid JSON" in str(exc.value)


def test_cli_writes_under_out_dir(tmp_path, monkeypatch):
    stub = GhStub({repo: [] for repo in ws.REPOS})
    monkeypatch.setattr(ws, "run_gh", stub)
    rc = ws.main(["--date", "2026-09-09", "--out-dir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "2026-09-09.md").is_file()


def test_cli_rejects_bad_date(tmp_path):
    rc = ws.main(["--date", "09-09-2026", "--out-dir", str(tmp_path)])
    assert rc == 2
    assert list(tmp_path.iterdir()) == []
