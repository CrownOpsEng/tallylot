from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
AGENTS_ROOT = REPO_ROOT / "agents"


def relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def display_path(path: Path) -> str:
    try:
        return relative_path(path)
    except ValueError:
        return str(path)
