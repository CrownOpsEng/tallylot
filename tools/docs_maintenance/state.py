from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
AGENTS_ROOT = REPO_ROOT / "agents"


def repo_root() -> Path:
    return REPO_ROOT


def docs_root() -> Path:
    return DOCS_ROOT


def agents_root() -> Path:
    return AGENTS_ROOT


def relative_path(path: Path) -> str:
    return path.relative_to(repo_root()).as_posix()


def display_path(path: Path) -> str:
    try:
        return relative_path(path)
    except ValueError:
        return str(path)
