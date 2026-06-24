#!/usr/bin/env python3
"""
Assemble the system portal's docs tree (SYS-008).

The portal is a GENERATED, read-only VIEW over the source repos — "aggregate, never
duplicate". This script copies each repo's real docs into a throwaway `portal/` tree
that MkDocs renders. Nothing here is authored by hand except the chrome in
`portal_src/`. Edit the sources in their own repos, then re-run:

    uv run --no-env-file --no-project python scripts/build_portal.py

Two jobs:
  1. Copy each repo's README / docs / decisions into portal/.
  2. Rewrite relative links so the portal is navigable AND every code reference becomes
     a one-click jump to GitHub (SYS-008, "code is always one click away"):
       - link to a doc we also copied   -> left relative (in-portal navigation)
       - link to source/config in repo  -> rewritten to github.com/<org>/<repo>/blob/...
       - link that resolves nowhere      -> left as-is (broken at the source, not here)

It is cwd-independent (paths resolve from this file) and reads the sibling repos as they
sit on disk next to `architecture/`. The same script runs in CI after the repos are
checked out, so local and published builds share one code path.
"""
from __future__ import annotations

import re
import shutil
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

# Matches inline markdown links and images: [text](target) / ![alt](target "title").
INLINE_LINK = re.compile(r'(!?\[[^\]]*\]\()([^)\s]+)((?:\s+"[^"]*")?\))')


def in_portal(repo_folder: str, rel: Path) -> bool:
    """True if the repo-relative path is something we copy into the portal."""
    parts = rel.parts
    if not parts:
        return False
    if repo_folder == "architecture":
        return parts[0] in ARCH_DIRS
    return parts[0] in APP_COPIED


def rewrite_links(text: str, md_rel: Path, repo_folder: str, repo_root: Path) -> str:
    """Resolve each relative link against the repo on disk and rewrite code refs to GitHub."""
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
    """Copy a repo subtree into the portal, rewriting links in every markdown file."""
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


def reset_portal() -> None:
    if PORTAL.exists():
        shutil.rmtree(PORTAL)
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


def main() -> None:
    reset_portal()
    copy_chrome()
    copy_arch_sections()
    copy_apps()
    write_indexes()
    pages = sum(1 for _ in PORTAL.rglob("*.md"))
    print(f"Portal assembled at {PORTAL} ({pages} pages).")


if __name__ == "__main__":
    main()
