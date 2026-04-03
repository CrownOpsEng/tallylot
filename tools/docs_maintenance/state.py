from __future__ import annotations

from pathlib import Path

from repo_support.paths import (
    agents_root as shared_agents_root,
)
from repo_support.paths import (
    display_repo_path,
    relative_repo_path,
)
from repo_support.paths import (
    docs_root as shared_docs_root,
)
from repo_support.paths import (
    repo_root as shared_repo_root,
)


def repo_root() -> Path:
    return shared_repo_root()


def docs_root() -> Path:
    return shared_docs_root()


def agents_root() -> Path:
    return shared_agents_root()


def relative_path(path: Path) -> str:
    return relative_repo_path(path)


def display_path(path: Path) -> str:
    return display_repo_path(path)
