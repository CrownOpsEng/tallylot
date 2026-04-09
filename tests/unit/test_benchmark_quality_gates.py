from __future__ import annotations

import subprocess
from pathlib import Path

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

    assert benchmark_quality_gates.main(["--strategy", "fast-current"]) == 0
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
