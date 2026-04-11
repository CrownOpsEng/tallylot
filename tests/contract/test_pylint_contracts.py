from __future__ import annotations

from pathlib import Path

from repo_support.paths import repo_root
from tools.run_pylint import _pylint_targets


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(root.rglob("*.py")))


def _production_python_files() -> tuple[Path, ...]:
    return tuple(
        path for path in _python_files(repo_root()) if "tests" not in path.parts
    )


def _is_covered(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def test_production_python_files_stay_within_repo_line_cap() -> None:
    offenders: list[tuple[Path, int]] = []
    exemptions: list[Path] = []

    for path in _production_python_files():
        text = path.read_text(encoding="utf-8")
        if "# pylint: disable=too-many-lines" in text:
            exemptions.append(path)
        line_count = len(text.splitlines())
        if line_count > 500:
            offenders.append((path, line_count))

    assert not exemptions, (
        f"production files still disable too-many-lines: {exemptions}"
    )
    assert not offenders, f"production files exceed the 500-line repo cap: {offenders}"


def test_pylint_targets_cover_all_repo_python_files() -> None:
    repo_root_path = repo_root()
    pylint_targets = _pylint_targets()
    repo_code_roots = tuple(
        repo_root_path / Path(argument) for argument in pylint_targets[0].command[4:]
    )
    test_roots = tuple(
        repo_root_path / Path(argument) for argument in pylint_targets[1].command[4:]
    )

    for path in _python_files(repo_root_path):
        if "tests" in path.parts:
            assert _is_covered(path, test_roots), (
                f"{path} is missing from test lint coverage"
            )
        else:
            assert _is_covered(path, repo_code_roots), (
                f"{path} is missing from repo lint coverage"
            )
