from __future__ import annotations

import subprocess

from pytest import CaptureFixture, MonkeyPatch

import tools.run_test_stress_checks as stress_checks


def test_stress_steps_match_repo_policy() -> None:
    steps = stress_checks._stress_steps()

    assert [step.name for step in steps] == [
        "fast-unit-seed-a",
        "fast-unit-seed-b",
        "contract-seed-a",
        "e2e-seed-a",
    ]
    assert steps[0].command == (
        "uv",
        "run",
        "pytest",
        "-n",
        "4",
        "-m",
        "unit and not slow",
        "--no-cov",
        "-q",
        "--randomly-seed",
        "1729",
    )
    assert steps[0].serial_fallback_command == (
        "uv",
        "run",
        "pytest",
        "-m",
        "unit and not slow",
        "--no-cov",
        "-q",
        "--randomly-seed",
        "1729",
    )
    assert steps[2].command == (
        "uv",
        "run",
        "pytest",
        "-m",
        "contract",
        "--no-cov",
        "-q",
        "--randomly-seed",
        "1729",
    )


def test_stress_runner_aggregates_failures_by_default(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    commands_seen: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check, env
        commands_seen.append(command)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert stress_checks.main([]) == 1
    assert commands_seen == [step.command for step in stress_checks._stress_steps()]
    output = capsys.readouterr().out
    assert "--randomly-seed 1729" in output
    assert "serial fallback" in output


def test_stress_runner_fail_fast_stops_after_first_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    commands_seen: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check, env
        commands_seen.append(command)
        returncode = 1 if len(commands_seen) == 2 else 0
        return subprocess.CompletedProcess(command, returncode, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert stress_checks.main(["--fail-fast"]) == 1
    assert commands_seen == [
        stress_checks._stress_steps()[0].command,
        stress_checks._stress_steps()[1].command,
    ]
