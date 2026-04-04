from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

_TEST_RCFILE = ".pylintrc-tests"


def _path_from_argument(argument: str) -> Path | None:
    if argument.startswith("-"):
        return None
    if argument.endswith(".py"):
        return Path(argument)
    return None


def _target_path(arguments: Sequence[str]) -> Path | None:
    for index, argument in enumerate(arguments):
        if argument == "--from-stdin" and index + 1 < len(arguments):
            return Path(arguments[index + 1])
        candidate = _path_from_argument(argument)
        if candidate is not None:
            return candidate
    return None


def _uses_test_rcfile(arguments: Sequence[str]) -> bool:
    return any(
        argument == f"--rcfile={_TEST_RCFILE}"
        or (
            argument == "--rcfile"
            and index + 1 < len(arguments)
            and arguments[index + 1] == _TEST_RCFILE
        )
        for index, argument in enumerate(arguments)
    )


def _should_use_test_rcfile(arguments: Sequence[str]) -> bool:
    target = _target_path(arguments)
    return target is not None and "tests" in target.parts


def _pylint_argv(arguments: Sequence[str]) -> tuple[str, ...]:
    if _uses_test_rcfile(arguments) or not _should_use_test_rcfile(arguments):
        return (sys.executable, "-m", "pylint", *arguments)
    return (sys.executable, "-m", "pylint", f"--rcfile={_TEST_RCFILE}", *arguments)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    result = subprocess.run(_pylint_argv(arguments), check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
