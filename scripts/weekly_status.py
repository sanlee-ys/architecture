"""Harvest merged pull requests from the last 7 days into a weekly status file.

The file is ``program/weekly/YYYY-MM-DD.md``. The date is the run day in UTC.
An empty week still writes a file that says zero merged PRs. That file is the
proof that the check ran. The harvest does not invent progress.

Repos
-----
``sanlee-ys/kb-agent``, ``sanlee-ys/notes-api``,
``sanlee-ys/defense-news-classifier``, ``sanlee-ys/architecture``.

Run locally:
    uv run python scripts/weekly_status.py
    uv run python scripts/weekly_status.py --date 2026-09-09
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "program" / "weekly"

REPOS = (
    "sanlee-ys/kb-agent",
    "sanlee-ys/notes-api",
    "sanlee-ys/defense-news-classifier",
    "sanlee-ys/architecture",
)

JSON_FIELDS = "number,title,url,mergedAt,author"

GhRunner = Callable[[Sequence[str]], str]


def run_gh(args: Sequence[str]) -> str:
    """Run ``gh`` and return stdout.

    Isolated as a module global so tests replace it. No test calls the network.

    Args:
        args: Arguments after ``gh``.

    Returns:
        Standard output from ``gh``.

    Raises:
        SystemExit: ``gh`` is missing, or ``gh`` exits non-zero.
    """
    try:
        completed = subprocess.run(
            ["gh", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("gh is not installed or is not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or "").strip() or "no stderr"
        raise SystemExit(f"gh failed ({exc.returncode}): {err}") from exc
    return completed.stdout


def utc_today() -> date:
    """Return the current UTC date."""
    return datetime.now(timezone.utc).date()


def window_start(today: date) -> date:
    """Return the first date in the 7-day window (inclusive).

    Args:
        today: The run day.

    Returns:
        ``today`` minus 7 days.
    """
    return today - timedelta(days=7)


def parse_merged_at(value: str) -> datetime:
    """Parse a GitHub ``mergedAt`` timestamp.

    Args:
        value: ISO-8601 time, usually ending in ``Z``.

    Returns:
        An aware UTC datetime.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def list_merged_prs(
    repo: str,
    start: date,
    end: date,
    run: GhRunner | None = None,
) -> list[dict]:
    """Return PRs in ``repo`` whose merge date is in ``[start, end]``.

    ``gh pr list --state merged`` returns the newest merged PRs. This function
    then keeps only rows whose ``mergedAt`` date sits in the window. The harvest
    does not use search text, so an open PR cannot enter the file.

    Args:
        repo: ``owner/name``.
        start: First date in the window (inclusive).
        end: Run day (inclusive).
        run: ``gh`` runner. Tests pass a stub. Default looks up ``run_gh``
            at call time so a monkeypatch on the module name is visible.

    Returns:
        A list of PR dicts, newest first.
    """
    if run is None:
        run = run_gh
    raw = run(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "merged",
            "--limit",
            "100",
            "--json",
            JSON_FIELDS,
        ]
    )
    try:
        rows = json.loads(raw or "[]")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"gh returned invalid JSON for {repo}: {exc}") from exc
    if not isinstance(rows, list):
        raise SystemExit(f"gh returned JSON that is not a list for {repo}.")

    kept: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        merged_at = row.get("mergedAt")
        if not merged_at:
            continue
        try:
            merged_day = parse_merged_at(str(merged_at)).date()
        except ValueError:
            continue
        if start <= merged_day <= end:
            kept.append(row)
    return kept


def _author_login(row: dict) -> str:
    author = row.get("author") or {}
    if isinstance(author, dict):
        login = author.get("login")
        if login:
            return str(login)
    return "unknown"


def render(today: date, start: date, by_repo: dict[str, list[dict]]) -> str:
    """Render the weekly markdown file.

    Args:
        today: The run day (file date).
        start: First date in the window.
        by_repo: Merged PRs keyed by ``owner/name``.

    Returns:
        Markdown text.
    """
    total = sum(len(rows) for rows in by_repo.values())
    lines = [
        f"# Weekly status — {today.isoformat()}",
        "",
        "This file lists pull requests that merged in the last 7 days.",
        f"The window is {start.isoformat()} through {today.isoformat()} (UTC).",
        "The harvest uses `gh`. The harvest does not invent progress.",
        "",
        "## Totals",
        "",
        f"- Merged pull requests: {total}",
        "",
    ]
    if total == 0:
        names = ", ".join(REPOS)
        lines.append(
            f"Zero merged PRs in {names} in this window."
        )
        lines.append("")
        return "\n".join(lines)

    for repo in REPOS:
        lines.append(f"## {repo}")
        lines.append("")
        rows = by_repo.get(repo, [])
        if not rows:
            lines.append("Zero merged pull requests.")
            lines.append("")
            continue
        for row in rows:
            number = row.get("number", "?")
            title = row.get("title", "(no title)")
            url = row.get("url", "")
            merged_at = row.get("mergedAt", "")
            try:
                merged_day = parse_merged_at(str(merged_at)).date().isoformat()
            except (TypeError, ValueError):
                merged_day = "unknown date"
            login = _author_login(row)
            if url:
                link = f"[#{number}]({url})"
            else:
                link = f"#{number}"
            lines.append(
                f"- {link}: {title} (merged {merged_day}, @{login})"
            )
        lines.append("")
    return "\n".join(lines)


def write_status(out_dir: Path, today: date, text: str) -> Path:
    """Write ``out_dir/YYYY-MM-DD.md`` and return the path.

    Args:
        out_dir: Destination directory. Created if missing.
        today: The run day.
        text: Markdown body.

    Returns:
        The path that was written.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{today.isoformat()}.md"
    path.write_text(text, encoding="utf-8")
    return path


def harvest(
    today: date,
    out_dir: Path,
    run: GhRunner | None = None,
) -> Path:
    """Harvest all four repos and write the weekly file.

    Args:
        today: The run day.
        out_dir: Destination directory.
        run: ``gh`` runner. Tests pass a stub. Default looks up ``run_gh``
            at call time so a monkeypatch on the module name is visible.

    Returns:
        The path that was written.
    """
    if run is None:
        run = run_gh
    start = window_start(today)
    by_repo = {repo: list_merged_prs(repo, start, today, run=run) for repo in REPOS}
    text = render(today, start, by_repo)
    return write_status(out_dir, today, text)


def main(argv: list[str] | None = None) -> int:
    """Parse flags, harvest, and write the weekly file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        help="Run day as YYYY-MM-DD (UTC). Default: today in UTC.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for YYYY-MM-DD.md. Default: program/weekly/.",
    )
    args = parser.parse_args(argv)

    if args.date:
        try:
            today = date.fromisoformat(args.date)
        except ValueError:
            print(f"Invalid --date {args.date!r}; expected YYYY-MM-DD.", file=sys.stderr)
            return 2
    else:
        today = utc_today()

    path = harvest(today, args.out_dir)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
