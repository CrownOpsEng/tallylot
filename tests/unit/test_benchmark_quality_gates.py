from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import tools.benchmark_quality_gates as benchmark_quality_gates


def test_benchmark_quality_gates_runs_selected_strategy(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    commands_seen: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del check, env
        commands_seen.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert (
        benchmark_quality_gates.main(
            ["--strategy", "fast-current", "--warmup-count", "0", "--iterations", "1"]
        )
        == 0
    )
    assert commands_seen == [
        (
            "uv",
            "run",
            "python",
            "-m",
            "tools.run_quality_gates",
            "--schedule",
            "all-at-once",
        )
    ]


def test_benchmark_quality_gates_strips_inherited_coverage_environment(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("COVERAGE_PROCESS_START", "stale-process-start")
    monkeypatch.setenv("COVERAGE_RCFILE", "stale-rcfile")

    environment = benchmark_quality_gates._benchmark_environment()

    assert "COVERAGE_PROCESS_START" not in environment
    assert "COVERAGE_RCFILE" not in environment


def test_benchmark_quality_gates_writes_json_summary(
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

    elapsed_values = iter((4.0, 6.0))

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        "tools.benchmark_quality_gates.time.perf_counter",
        lambda: next(elapsed_values),
    )

    assert (
        benchmark_quality_gates.main(
            [
                "--strategy",
                "fast-current",
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
    assert payload["strategies"][0]["name"] == "fast-current"
    assert payload["strategies"][0]["median_elapsed_seconds"] == 2.0


def test_benchmark_quality_gates_rejects_invalid_iteration_counts() -> None:
    with pytest.raises(SystemExit, match="--iterations must be at least 1"):
        benchmark_quality_gates.main(["--iterations", "0"])
