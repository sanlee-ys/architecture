#!/usr/bin/env python3
"""
Assemble the system portal's docs tree (architecture/ADR-001, formerly SYS-008).

The portal is a GENERATED, read-only VIEW over the source repos — "aggregate, never
duplicate". This script copies each repo's real docs into a throwaway `portal/` tree
that MkDocs renders. Nothing here is authored by hand except the chrome in
`portal_src/`. Edit the sources in their own repos, then re-run:

    uv run --no-env-file --no-project python scripts/build_portal.py

Three jobs:
  1. Copy each repo's README / docs / decisions into portal/.
  2. Rewrite relative links so the portal is navigable AND every code reference becomes
     a one-click jump to GitHub (architecture/ADR-001, "code is always one click away"):
       - link to a doc we also copied   -> left relative (in-portal navigation)
       - link to source/config in repo  -> rewritten to github.com/<org>/<repo>/blob/...
       - link that resolves nowhere      -> left as-is (broken at the source, not here)
  3. Generate the Roadmap page (architecture/ADR-002) from program/README.md's Now/Next/Later section
     plus each app's live pyproject.toml version — no roadmap state is hand-duplicated.

It is cwd-independent (paths resolve from this file) and reads the sibling repos as they
sit on disk next to `architecture/`. The same script runs in CI after the repos are
checked out, so local and published builds share one code path.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import tomllib
from pathlib import Path
from urllib.parse import urlparse

# --- locations ---------------------------------------------------------------
ARCH = Path(__file__).resolve().parent.parent      # the architecture repo
ROOT = ARCH.parent                                  # the Projects folder (sibling repos live here)
PORTAL = ARCH / "portal"                            # generated docs_dir (gitignored)
SRC = ARCH / "portal_src"                           # hand-authored portal-only chrome

GH = "https://github.com/sanlee-ys"                 # repo home for the "jump to code" links

# Apps to aggregate fully: (repo folder, display name). learning-notes has its own
# published site and a different audience, so it's linked from the launchpad, not
# re-rendered here.
APPS = [
    ("kb-agent", "kb-agent"),
    ("notes-api", "notes-api"),
    ("defense-news-classifier", "defense-news-classifier"),
]

# architecture's own doc dirs, mirrored under portal/ with the SAME names so the repo's
# internal relative links (e.g. SYS-007 -> ../product/one-pager.md) keep working.
ARCH_DIRS = ["decisions", "program", "engineering", "case-study", "product", "reference"]

# Per repo, which top-level dirs we actually copy into the portal. A link landing inside
# one of these is navigable in-portal and stays relative; anything else points to source.
APP_COPIED = {"docs", "decisions"}

# program/README.md tags its Now/Next/Later bullets with a short workstream label
# (e.g. "**[classifier]**"), not the repo folder name. Map the ones that mean an app repo;
# everything else (cross-cutting, product, program, ops, non-goal, ...) is cross-cutting.
ROADMAP_TAG_TO_FOLDER = {
    "classifier": "defense-news-classifier",
    "notes-api": "notes-api",
    "kb-agent": "kb-agent",
}

ROADMAP_BULLET = re.compile(r"^- \*\*\[([\w-]+)\]\*\*\s*(.*)$")
ROADMAP_BUCKET_HEADING = re.compile(r"^### (Now|Next|Later)\b")

# Matches inline markdown links and images: [text](target) / ![alt](target "title").
INLINE_LINK = re.compile(r'(!?\[[^\]]*\]\()([^)\s]+)((?:\s+"[^"]*")?\))')


def in_portal(repo_folder: str, rel: Path) -> bool:
    """Return whether a repo-relative path is something we copy into the portal.

    Args:
        repo_folder: The source repo's folder name (e.g. "architecture", "notes-api").
        rel: A path relative to that repo's root.

    Returns:
        True if the path lands inside a subtree the portal aggregates, so an
        in-portal link to it stays relative rather than being rewritten to GitHub.
    """
    parts = rel.parts
    if not parts:
        return False
    if repo_folder == "architecture":
        return parts[0] in ARCH_DIRS
    return parts[0] in APP_COPIED


def rewrite_links(text: str, md_rel: Path, repo_folder: str, repo_root: Path) -> str:
    """Rewrite a Markdown file's relative links for the portal.

    Each relative link is resolved against the repo on disk: links to docs the
    portal also copies stay relative, links to source/config are rewritten to a
    GitHub blob/tree URL, and links that resolve nowhere are left untouched.

    Args:
        text: The Markdown file's full contents.
        md_rel: The file's path relative to its repo root (used to resolve links).
        repo_folder: The source repo's folder name.
        repo_root: Absolute path to the source repo on disk.

    Returns:
        The Markdown text with links rewritten per the rules above.
    """
    src_dir = (repo_root / md_rel).parent
    root = repo_root.resolve()

    def repl(match: re.Match) -> str:
        pre, href, post = match.group(1), match.group(2), match.group(3)
        # Leave external (http/mailto/…), root-absolute, and pure-anchor links alone.
        if href.startswith(("#", "/")) or urlparse(href).scheme:
            return match.group(0)
        target, _, frag = href.partition("#")
        if not target:
            return match.group(0)
        resolved = (src_dir / target).resolve()
        if not resolved.exists():
            return match.group(0)            # broken in the source too — don't fabricate
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            return match.group(0)            # escapes the repo — leave it
        if in_portal(repo_folder, rel):
            return match.group(0)            # a copied doc — relative link works in-portal
        kind = "tree" if resolved.is_dir() else "blob"
        url = f"{GH}/{repo_folder}/{kind}/main/{rel.as_posix()}"
        tail = f"#{frag}" if (frag and kind == "blob") else ""
        return f"{pre}{url}{tail}{post}"

    return INLINE_LINK.sub(repl, text)


def aggregate_tree(repo_folder: str, repo_root: Path, src: Path, dest: Path, rel_base: Path) -> None:
    """Copy a repo subtree into the portal, rewriting links in every Markdown file.

    Args:
        repo_folder: The source repo's folder name.
        repo_root: Absolute path to the source repo on disk.
        src: The subtree to copy from.
        dest: Where to write the copied subtree under the portal.
        rel_base: The current path relative to the repo root, accumulated as
            recursion descends so links resolve correctly.
    """
    for child in sorted(src.iterdir()):
        rel = rel_base / child.name
        out = dest / child.name
        if child.is_dir():
            aggregate_tree(repo_folder, repo_root, child, out, rel)
        elif child.suffix == ".md":
            out.parent.mkdir(parents=True, exist_ok=True)
            text = child.read_text(encoding="utf-8")
            out.write_text(rewrite_links(text, rel, repo_folder, repo_root), encoding="utf-8")
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, out)


def _force_writable(func, path, _exc) -> None:
    """rmtree error handler: clear the read-only bit and retry once.

    On Windows a read-only directory cannot be removed at all, and `git` sets that
    bit on files it copies out of some checkouts — so a portal/ left over from a
    previous run makes the next build die with WinError 5 (Access is denied) on a
    directory that is otherwise empty. It bit twice on 2026-07-19 and both times
    the fix was clearing the attribute by hand, which is a build step masquerading
    as a chore.

    CI never hits this (fresh checkout, no leftover portal/), which is exactly why
    it survived: the failure only reaches the one person running the build locally,
    and it looks like a permissions problem with their machine rather than a bug in
    the script.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def reset_portal() -> None:
    if PORTAL.exists():
        shutil.rmtree(PORTAL, onexc=_force_writable)
    PORTAL.mkdir(parents=True)


def copy_chrome() -> None:
    """Hand-authored portal-only pages: the landing launchpad and the telemetry stub."""
    for item in SRC.iterdir():
        dest = PORTAL / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def copy_arch_sections() -> None:
    for name in ARCH_DIRS:
        src = ARCH / name
        if src.exists():
            aggregate_tree("architecture", ARCH, src, PORTAL / name, Path(name))
    # The ADR template isn't a decision — keep it out of the rendered wall.
    template = PORTAL / "decisions" / "TEMPLATE.md"
    if template.exists():
        template.unlink()


def copy_apps() -> None:
    apps_root = PORTAL / "apps"
    apps_root.mkdir(exist_ok=True)
    for folder, name in APPS:
        repo = ROOT / folder
        dest = apps_root / folder
        dest.mkdir(parents=True, exist_ok=True)
        # The repo README becomes the app's landing page, with a code-jump button on top.
        readme = repo / "README.md"
        if readme.exists():
            body = rewrite_links(readme.read_text(encoding="utf-8"), Path("README.md"), folder, repo)
        else:
            body = f"# {name}\n"
        button = f"[Code on GitHub ↗]({GH}/{folder}){{ .md-button .md-button--primary }}\n\n"
        (dest / "index.md").write_text(button + body, encoding="utf-8")
        # Pull in the repo's docs/ and decisions/ verbatim where they exist (links rewritten).
        for sub in ("docs", "decisions"):
            s = repo / sub
            if s.exists():
                aggregate_tree(folder, repo, s, dest / sub, Path(sub))


def write_indexes() -> None:
    # Apps index (links are relative to portal/apps/).
    cards = "\n".join(
        f"- **[{name}]({folder}/index.md)** — [code on GitHub ↗]({GH}/{folder})"
        for folder, name in APPS
    )
    (PORTAL / "apps" / "index.md").write_text(
        "# Apps\n\nEach app's README, docs, and decisions — one click from its source.\n\n"
        + cards + "\n",
        encoding="utf-8",
    )
    # Decisions wall: SYS-* live here; each app's ADRs are linked in place.
    sys_files = sorted((PORTAL / "decisions").glob("SYS-*.md"))
    sys_rows = "\n".join(f"- [{f.stem}]({f.name})" for f in sys_files)
    app_rows = "\n".join(
        f"- [{name} ADRs](../apps/{folder}/decisions/)" for folder, name in APPS
    )
    (PORTAL / "decisions" / "index.md").write_text(
        "# Decisions\n\nThe whole decision log in one wall — system-level (`SYS-*`) "
        "and per-app (`ADR-*`).\n\n"
        "## System (SYS-*)\n\n" + sys_rows + "\n\n"
        "## Per-app (ADR-*)\n\n" + app_rows + "\n",
        encoding="utf-8",
    )


def read_version(folder: str) -> str:
    """Read an app's live version straight from its pyproject.toml.

    Never duplicated into a second file — architecture/ADR-002 (this dashboard cannot drift
    from reality).

    Args:
        folder: The app repo's folder name, a sibling of the architecture repo.

    Returns:
        The version string from ``[project] version``, or "—" if the file or
        field is absent.
    """
    pyproject = ROOT / folder / "pyproject.toml"
    if not pyproject.exists():
        return "—"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data.get("project", {}).get("version", "—")


def parse_roadmap() -> dict[str, list[tuple[str, str]]]:
    """Parse the Now/Next/Later bullets from program/README.md's roadmap section.

    The section runs from its own heading to the next top-level '## '.

    Returns:
        A dict keyed by bucket ("Now", "Next", "Later"), each mapping to a list
        of (tag, text) pairs — the short workstream label and the bullet body.
    """
    readme = (ARCH / "program" / "README.md").read_text(encoding="utf-8").splitlines()
    buckets: dict[str, list[tuple[str, str]]] = {"Now": [], "Next": [], "Later": []}
    in_section = False
    bucket = None
    for line in readme:
        if line.startswith("## Roadmap"):
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("## "):
            break  # left the roadmap section
        heading = ROADMAP_BUCKET_HEADING.match(line)
        if heading:
            bucket = heading.group(1)
            continue
        bullet = ROADMAP_BULLET.match(line)
        if bullet and bucket:
            buckets[bucket].append((bullet.group(1), bullet.group(2)))
    return buckets


def write_roadmap() -> None:
    """Generate the Roadmap page (architecture/ADR-002): one card per app with its live version and
    Now/Next/Later items, plus a cross-cutting list for tags that aren't an app repo.
    Everything here is read from program/README.md and each app's pyproject.toml —
    nothing on this page is authored by hand."""
    buckets = parse_roadmap()

    cards = []
    for folder, name in APPS:
        version = read_version(folder)
        lines = [f"-   **{name}** `v{version}`", "", "    ---"]
        has_items = False
        for bucket_name in ("Now", "Next", "Later"):
            items = [
                text for tag, text in buckets[bucket_name]
                if ROADMAP_TAG_TO_FOLDER.get(tag) == folder
            ]
            if not items:
                continue
            has_items = True
            lines.append(f"\n    **{bucket_name}**\n")
            for text in items:
                lines.append(f"    - {text}")
        if not has_items:
            lines.append("\n    Nothing in flight — see [Program](program/README.md) for what shipped.")
        cards.append("\n".join(lines))

    cross_cutting = []
    for bucket_name in ("Now", "Next", "Later"):
        items = [
            (tag, text) for tag, text in buckets[bucket_name]
            if tag not in ROADMAP_TAG_TO_FOLDER
        ]
        if not items:
            continue
        cross_cutting.append(f"\n**{bucket_name}**\n")
        for tag, text in items:
            cross_cutting.append(f"- **[{tag}]** {text}")

    page = (
        "# Roadmap\n\n"
        "The system's status at a glance — generated from "
        "[`program/README.md`](program/README.md#roadmap-now-next-later) (the curated "
        "Now/Next/Later plan) and each app's live version. Edit the source, not this page "
        "(`architecture/ADR-002`).\n\n"
        '<div class="grid cards" markdown>\n\n'
        + "\n\n".join(cards)
        + "\n\n</div>\n\n"
        "## Cross-cutting & program\n"
        + "\n".join(cross_cutting) + "\n"
    )
    (PORTAL / "roadmap.md").write_text(page, encoding="utf-8")


def main() -> None:
    reset_portal()
    copy_chrome()
    copy_arch_sections()
    copy_apps()
    write_indexes()
    write_roadmap()
    pages = sum(1 for _ in PORTAL.rglob("*.md"))
    print(f"Portal assembled at {PORTAL} ({pages} pages).")


if __name__ == "__main__":
    main()
