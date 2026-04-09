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


def test_benchmark_tests_cleans_coverage_files_for_full_suite(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    coverage_path = tmp_path / ".coverage"
    coverage_path.write_text("stale", encoding="utf-8")

    def fake_run(
        command: tuple[str, ...],
        *,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del check, env
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert benchmark_tests.main(["--suite", "full"]) == 0
    assert coverage_path.exists() is False
