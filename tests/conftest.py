"""Make `scripts/` importable from the tests without packaging the repo.

This repo is a document registry that happens to carry three guard scripts; it is not a
Python distribution and should not grow a `pyproject.toml`, an `src/` layout and an
editable install just so a test file can say `import check_program_metrics`. So the path
is prepended here instead. The scripts are deliberately module-level-function shaped —
`fetch_artifact` and `fetch_text` are plain module globals — which is what makes them
monkeypatchable without any of that machinery.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
