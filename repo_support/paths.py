from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
_ACTIVE_REPO_ROOT = _DEFAULT_REPO_ROOT


def _normalize_root(path: Path) -> Path:
    return path.expanduser().resolve()


def repo_root() -> Path:
    return _ACTIVE_REPO_ROOT


def set_repo_root(path: Path) -> None:
    global _ACTIVE_REPO_ROOT
    _ACTIVE_REPO_ROOT = _normalize_root(path)


def reset_repo_root() -> None:
    global _ACTIVE_REPO_ROOT
    _ACTIVE_REPO_ROOT = _DEFAULT_REPO_ROOT


@contextmanager
def override_repo_root(path: Path) -> Iterator[Path]:
    previous_root = repo_root()
    set_repo_root(path)
    try:
        yield repo_root()
    finally:
        set_repo_root(previous_root)


def src_root() -> Path:
    return repo_root() / "src"


def tests_root() -> Path:
    return repo_root() / "tests"


def fixtures_root() -> Path:
    return tests_root() / "fixtures"


def adapter_packs_root() -> Path:
    return fixtures_root() / "adapter_packs"


def docs_root() -> Path:
    return repo_root() / "docs"


def agents_root() -> Path:
    return repo_root() / "agents"


def claude_commands_root() -> Path:
    return repo_root() / ".claude" / "commands"


def vscode_settings_path() -> Path:
    return repo_root() / ".vscode" / "settings.json"


def relative_repo_path(path: Path) -> str:
    return path.relative_to(repo_root()).as_posix()


def display_repo_path(path: Path) -> str:
    try:
        return relative_repo_path(path)
    except ValueError:
        return str(path)
