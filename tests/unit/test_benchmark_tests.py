from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import tools.benchmark_tests as benchmark_tests


def test_benchmark_tests_exposes_expected_comparison_suites() -> None:
    assert [suite.name for suite in benchmark_tests.SUITES] == [
        "fast-unit-serial",
        "fast-unit-n4",
        "fast-unit-nauto",
        "full-serial",
        "full-nauto",
    ]


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

    assert (
        benchmark_tests.main(
            ["--suite", "full-serial", "--warmup-count", "0", "--iterations", "1"]
        )
        == 0
    )
    assert "COVERAGE_FILE" in captured_environment
    assert Path(captured_environment["COVERAGE_FILE"]).is_absolute()
    assert Path(captured_environment["COVERAGE_FILE"]).name == ".coverage"


def test_benchmark_tests_strips_inherited_coverage_environment(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("COVERAGE_PROCESS_START", "stale-process-start")
    monkeypatch.setenv("COVERAGE_RCFILE", "stale-rcfile")

    environment = benchmark_tests._suite_environment(benchmark_tests.SUITES[0])

    assert "COVERAGE_PROCESS_START" not in environment
    assert "COVERAGE_RCFILE" not in environment


def test_benchmark_tests_writes_json_summary(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "benchmark.json"

    def fake_run(
        command: tuple[str, ...],
        *,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del check, env
        return subprocess.CompletedProcess(command, 0)

    elapsed_values = iter((2.0, 5.5))

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        "tools.benchmark_tests.time.perf_counter",
        lambda: next(elapsed_values),
    )

    assert (
        benchmark_tests.main(
            [
                "--suite",
                "fast-unit-n4",
                "--warmup-count",
                "0",
                "--iterations",
                "1",
                "--json-out",
                str(output_path),
            ]
        )
        == 0
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["warmup_count"] == 0
    assert payload["measured_iterations"] == 1
    assert payload["suites"][0]["name"] == "fast-unit-n4"
    assert payload["suites"][0]["median_elapsed_seconds"] == 3.5


def test_benchmark_tests_reject_invalid_iteration_counts() -> None:
    with pytest.raises(SystemExit, match="--warmup-count must be zero or greater"):
        benchmark_tests.main(["--warmup-count", "-1"])
