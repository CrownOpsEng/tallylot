from __future__ import annotations

import subprocess
from pathlib import Path

from pytest import MonkeyPatch

import tools.benchmark_tests as benchmark_tests


def test_benchmark_tests_adds_xdist_after_pytest_invocation() -> None:
    suite = benchmark_tests.SUITES[0]

    assert benchmark_tests._command_for_suite(suite, parallel=True) == (
        "uv",
        "run",
        "pytest",
        "-n",
        "auto",
        "tests/unit",
        "--no-cov",
        "-q",
        "--durations=10",
    )


def test_benchmark_tests_full_suite_uses_isolated_coverage_file(
    monkeypatch: MonkeyPatch,
) -> None:
    captured_environment: dict[str, str] = {}

    def fake_run(
        command: tuple[str, ...],
        *,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del check
        captured_environment.update(env)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert benchmark_tests.main(["--suite", "full"]) == 0
    assert "COVERAGE_FILE" in captured_environment
    assert Path(captured_environment["COVERAGE_FILE"]).is_absolute()
    assert Path(captured_environment["COVERAGE_FILE"]).name == ".coverage"
