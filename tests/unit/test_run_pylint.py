from __future__ import annotations

import sys

from tools.run_pylint import TARGETS, PylintTarget


def test_pylint_targets_split_repo_code_from_tests() -> None:
    expected_targets = (
        PylintTarget(
            name="src-tools",
            command=(sys.executable, "-m", "pylint", "src", "tools", "conftest.py"),
        ),
        PylintTarget(
            name="tests",
            command=(sys.executable, "-m", "pylint", "--disable=protected-access", "tests"),
        ),
    )

    assert expected_targets == TARGETS
