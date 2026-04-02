from __future__ import annotations

import sys

from repo_support.paths import repo_root
from tools.run_pylint import _PylintTarget, _TARGETS


def test_pylint_targets_split_repo_code_from_tests() -> None:
    expected_targets = (
        _PylintTarget(
            name="src-tools",
            command=(sys.executable, "-m", "pylint", "src", "tools", "conftest.py"),
        ),
        _PylintTarget(
            name="tests",
            command=(sys.executable, "-m", "pylint", "--rcfile=.pylintrc-tests", "tests"),
        ),
    )

    assert expected_targets == _TARGETS


def test_test_pylint_rcfile_disables_protected_access() -> None:
    config_text = (repo_root() / ".pylintrc-tests").read_text(encoding="utf-8")

    assert "protected-access" in config_text
