from __future__ import annotations
import sys
from pathlib import Path

import pytest

from repo_support import paths as repo_paths
from repo_support.paths import repo_root
import tools.run_pylint
from tools.run_pylint import _ADAPTER_TEST_IGNORE_PATHS, _PylintTarget, _pylint_targets


def test_pylint_targets_split_repo_code_from_tests() -> None:
    targets = _pylint_targets()

    assert targets[0] == _PylintTarget(
        name="repo-code",
        command=(
            sys.executable,
            "-m",
            "pylint",
            f"--ignore-paths={_ADAPTER_TEST_IGNORE_PATHS}",
            "src",
            "tools",
            "repo_support",
            "conftest.py",
        ),
    )
    assert targets[1].name == "tests"
    assert targets[1].command[:5] == (
        sys.executable,
        "-m",
        "pylint",
        "--rcfile=.pylintrc-tests",
        "tests",
    )


def test_pylint_targets_include_colocated_adapter_tests(tmp_path: Path) -> None:
    (
        tmp_path
        / "src"
        / "tallylot"
        / "adapters"
        / "sources"
        / "wallets"
        / "demo"
        / "tests"
    ).mkdir(
        parents=True,
    )

    with repo_paths.override_repo_root(tmp_path):
        targets = _pylint_targets()

    assert targets[1].command == (
        sys.executable,
        "-m",
        "pylint",
        "--rcfile=.pylintrc-tests",
        "tests",
        "src/tallylot/adapters/sources/wallets/demo/tests",
    )


def test_test_pylint_rcfile_disables_protected_access() -> None:
    config_text = (repo_root() / ".pylintrc-tests").read_text(encoding="utf-8")

    assert "protected-access" in config_text


def test_run_pylint_main_runs_all_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = (
        _PylintTarget(name="repo-code", command=("python", "-m", "pylint", "src")),
        _PylintTarget(name="tests", command=("python", "-m", "pylint", "tests")),
    )
    seen: list[str] = []

    monkeypatch.setattr(tools.run_pylint, "_pylint_targets", lambda: targets)

    def fake_run_target(target: _PylintTarget) -> tools.run_pylint._PylintResult:
        seen.append(target.name)
        return tools.run_pylint._PylintResult(
            target=target,
            returncode=0,
            stdout="ok",
            stderr="",
            elapsed=0.1,
        )

    monkeypatch.setattr(tools.run_pylint, "_run_target", fake_run_target)

    assert tools.run_pylint.main(()) == 0
    assert sorted(seen) == ["repo-code", "tests"]
