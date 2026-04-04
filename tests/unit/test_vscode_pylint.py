from __future__ import annotations

import sys

from tools.vscode_pylint import _pylint_argv


def test_test_files_use_test_pylint_rcfile() -> None:
    argv = _pylint_argv(("tests/unit/test_quality_gates.py",))

    assert argv == (
        sys.executable,
        "-m",
        "pylint",
        "--rcfile=.pylintrc-tests",
        "tests/unit/test_quality_gates.py",
    )


def test_non_test_files_use_base_pylint_config() -> None:
    argv = _pylint_argv(("tools/run_pylint.py",))

    assert argv == (
        sys.executable,
        "-m",
        "pylint",
        "tools/run_pylint.py",
    )


def test_from_stdin_uses_test_pylint_rcfile_for_test_paths() -> None:
    argv = _pylint_argv(
        (
            "--from-stdin",
            "tests/unit/test_quality_gates.py",
        )
    )

    assert argv == (
        sys.executable,
        "-m",
        "pylint",
        "--rcfile=.pylintrc-tests",
        "--from-stdin",
        "tests/unit/test_quality_gates.py",
    )


def test_existing_rcfile_is_preserved() -> None:
    argv = _pylint_argv(
        (
            "--rcfile=.pylintrc-tests",
            "tests/unit/test_quality_gates.py",
        )
    )

    assert argv == (
        sys.executable,
        "-m",
        "pylint",
        "--rcfile=.pylintrc-tests",
        "tests/unit/test_quality_gates.py",
    )
