from __future__ import annotations

import subprocess
from pathlib import Path

from pytest import MonkeyPatch

import tools.benchmark_quality_gates as benchmark_quality_gates


def _successful_completed_process(
    command: tuple[str, ...],
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, 0)


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


def test_benchmark_quality_gates_cleans_coverage_files(tmp_path: Path) -> None:
    coverage_path = tmp_path / ".coverage"
    coverage_path.write_text("stale", encoding="utf-8")

    with MonkeyPatch.context() as monkeypatch:
        monkeypatch.chdir(tmp_path)

        def fake_run(
            command: tuple[str, ...],
            *,
            check: bool,
            env: dict[str, str],
        ) -> subprocess.CompletedProcess[str]:
            del check, env
            return _successful_completed_process(command)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert benchmark_quality_gates.main(["--strategy", "fast-optimized"]) == 0

    assert coverage_path.exists() is False
