from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import tools.run_quality_gates
from repo_support.paths import repo_root
from tools.run_quality_gates import (
    QualityGate,
    _DEFAULT_TEST_COMMAND,
    _FULL_TEST_COMMAND,
    _quality_gates,
)


def test_quality_gates_default_to_fast_commit_time_pytest() -> None:
    gates = _quality_gates(full_tests=False)

    assert [gate.name for gate in gates] == [
        "markdownlint",
        "actionlint",
        "ruff",
        "mypy",
        "pyright",
        "pylint",
        "pytest",
    ]
    assert gates[0].command == ("uv", "run", "pre-commit", "run", "markdownlint", "--all-files")
    assert gates[1].command == ("uv", "run", "actionlint", "-color")
    assert gates[4].command == ("uv", "run", "pyright")
    assert gates[5].command == ("uv", "run", "python", "-m", "tools.run_pylint")
    assert gates[-1].command == _DEFAULT_TEST_COMMAND


def test_quality_gates_can_switch_to_full_pytest() -> None:
    gates = _quality_gates(full_tests=True)

    assert gates[-1].command == _FULL_TEST_COMMAND


def test_run_gate_exports_external_uv_project_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_environment: dict[str, str] = {}

    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert check is False
        captured_environment.update(env)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    gate = _quality_gates(full_tests=False)[0]
    tools.run_quality_gates._run_gate(gate)

    assert captured_environment["UV_PROJECT_ENVIRONMENT"] == str(Path.home() / ".venvs" / "tallylot-py312")


def test_pre_commit_config_excludes_pylint_hook() -> None:
    config_text = (repo_root() / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "id: pylint" not in config_text
    assert "name: pytest-fast" in config_text


def test_quality_gates_refresh_generated_pyright_config_before_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_sync_pyright_config() -> bool:
        calls.append("sync")
        return False

    def fake_quality_gates(*, full_tests: bool) -> tuple[QualityGate, ...]:
        del full_tests
        return (QualityGate(name="noop", command=("uv",)),)

    def fake_run_gate(
        gate: QualityGate,
    ) -> tuple[QualityGate, subprocess.CompletedProcess[str], float]:
        return gate, subprocess.CompletedProcess(gate.command, 0, stdout="", stderr=""), 0.0

    monkeypatch.setattr(
        tools.run_quality_gates,
        "sync_pyright_config",
        fake_sync_pyright_config,
    )
    monkeypatch.setattr(tools.run_quality_gates, "_quality_gates", fake_quality_gates)
    monkeypatch.setattr(tools.run_quality_gates, "_run_gate", fake_run_gate)

    assert tools.run_quality_gates.main(()) == 0

    assert calls == ["sync"]


def test_quality_gates_fail_when_generated_pyright_config_was_stale(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_quality_gates(*, full_tests: bool) -> tuple[QualityGate, ...]:
        del full_tests
        return ()

    monkeypatch.setattr(tools.run_quality_gates, "sync_pyright_config", lambda: True)
    monkeypatch.setattr(tools.run_quality_gates, "_quality_gates", fake_quality_gates)

    assert tools.run_quality_gates.main(()) == 1

    assert "pyrightconfig.tests.json was out of sync" in capsys.readouterr().out
