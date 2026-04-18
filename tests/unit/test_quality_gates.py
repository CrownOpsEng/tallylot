from __future__ import annotations

import subprocess
import threading

import pytest

from repo_support.paths import repo_root
from repo_support.pytest_commands import (
    DEFAULT_FAST_PYTEST_WORKERS,
    build_fast_pytest_command,
)
from repo_support.quality_gates import (
    QUALITY_GATE_ORDER,
    QualityGate,
    QualityPhase,
    available_quality_gates,
)
import tools.run_quality_gates
from tools.run_quality_gates import _phase_plan, _run_request


def test_quality_gates_default_to_repo_benchmarked_fast_schedule() -> None:
    parse_args = getattr(tools.run_quality_gates, "_parse_args")
    run_request = _run_request(parse_args(()))

    assert _phase_plan(run_request) == (
        QualityPhase(name="all-at-once", gate_names=QUALITY_GATE_ORDER),
    )


def test_quality_gates_default_to_all_at_once_for_full_tests() -> None:
    parse_args = getattr(tools.run_quality_gates, "_parse_args")
    run_request = _run_request(parse_args(("--full-tests",)))

    assert _phase_plan(run_request) == (
        QualityPhase(name="all-at-once", gate_names=QUALITY_GATE_ORDER),
    )


def test_quality_gates_can_select_named_gates() -> None:
    parse_args = getattr(tools.run_quality_gates, "_parse_args")
    run_request = _run_request(
        parse_args(("--gate", "markdownlint", "--gate", "pytest"))
    )

    assert _phase_plan(run_request) == (
        QualityPhase(name="all-at-once", gate_names=("markdownlint", "pytest")),
    )


def test_fast_quality_gate_uses_shared_pytest_command_builder() -> None:
    assert available_quality_gates(full_tests=False)["pytest"].command == (
        build_fast_pytest_command()
    )


def test_fast_pytest_defaults_to_four_workers() -> None:
    assert build_fast_pytest_command() == (
        "pytest",
        "-n",
        str(DEFAULT_FAST_PYTEST_WORKERS),
        "-m",
        "unit and not slow",
        "--no-cov",
        "-q",
    )


@pytest.mark.parametrize(
    ("worker_override", "expected_command"),
    [
        (
            "4",
            (
                "pytest",
                "-n",
                "4",
                "-m",
                "unit and not slow",
                "--no-cov",
                "-q",
            ),
        ),
        (
            "1",
            (
                "pytest",
                "-n",
                "1",
                "-m",
                "unit and not slow",
                "--no-cov",
                "-q",
            ),
        ),
        (
            "0",
            ("pytest", "-m", "unit and not slow", "--no-cov", "-q"),
        ),
    ],
)
def test_fast_pytest_honors_worker_override(
    monkeypatch: pytest.MonkeyPatch,
    worker_override: str,
    expected_command: tuple[str, ...],
) -> None:
    monkeypatch.setenv("TALLYLOT_FAST_PYTEST_WORKERS", worker_override)

    assert build_fast_pytest_command() == expected_command


def test_run_gate_ignores_repo_local_dot_venv_for_subprocesses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    monkeypatch.setenv("VIRTUAL_ENV", str(repo_root() / ".venv"))
    monkeypatch.setenv("PATH", "/tmp/test-bin")

    gate = available_quality_gates(full_tests=False)["markdownlint"]
    tools.run_quality_gates._run_gate(gate)

    assert captured_environment["PATH"] == (
        f"{captured_environment['UV_PROJECT_ENVIRONMENT']}/bin:/tmp/test-bin"
    )
    assert (
        captured_environment["VIRTUAL_ENV"]
        == captured_environment["UV_PROJECT_ENVIRONMENT"]
    )
    assert captured_environment["UV_PROJECT_ENVIRONMENT"].endswith(
        ".venvs/tallylot-py312"
    )


def test_run_gate_sets_absolute_coverage_config_for_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_environment: dict[str, str] = {}

    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check
        captured_environment.update(env)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    gate = available_quality_gates(full_tests=True)["pytest"]
    tools.run_quality_gates._run_gate(gate)

    coverage_config = str(repo_root() / "pyproject.toml")
    assert coverage_config in captured_environment["PYTEST_ADDOPTS"]
    assert "COVERAGE_FILE" not in captured_environment


def test_run_phase_executes_gates_concurrently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    barrier = threading.Barrier(2)

    def fake_run_gate(gate: QualityGate) -> tools.run_quality_gates.GateResult:
        barrier.wait(timeout=1.0)
        return tools.run_quality_gates.GateResult(
            gate=gate,
            returncode=0,
            stdout="",
            stderr="",
            elapsed=0.0,
        )

    monkeypatch.setattr(tools.run_quality_gates, "_run_gate", fake_run_gate)
    available_gates = available_quality_gates(full_tests=False)

    phase_result = tools.run_quality_gates._run_phase(
        QualityPhase(name="parallel-check", gate_names=("markdownlint", "ruff")),
        available_gates=available_gates,
    )

    assert tuple(
        gate_result.gate.name for gate_result in phase_result.gate_results
    ) == ("markdownlint", "ruff")


def test_pre_commit_config_keeps_hook_validations_without_ruff_duplication() -> None:
    config_text = (repo_root() / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "id: markdownlint" in config_text
    assert "id: commit-message" in config_text
    assert "id: mypy" not in config_text
    assert "id: pyright" not in config_text
    assert "name: pytest-fast" not in config_text
    assert "id: ruff" not in config_text


def test_pre_commit_config_keeps_single_pass_checkpoint_validations() -> None:
    config_text = (repo_root() / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert config_text.count("id: markdownlint") == 1
    assert config_text.count("id: commit-message") == 1
    assert "id: mypy" not in config_text
    assert "id: pyright" not in config_text
    assert "name: pytest-fast" not in config_text
    assert "tools.run_quality_gates" not in config_text
    assert "tools.run_ci_parity_checks" not in config_text


def test_quality_gates_refresh_generated_pyright_config_before_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_sync_pyright_config() -> bool:
        calls.append("sync")
        return False

    def fake_phase_plan(
        run_request: tools.run_quality_gates._RunRequest,
    ) -> tuple[QualityPhase, ...]:
        del run_request
        return (QualityPhase(name="noop", gate_names=("ruff",)),)

    def fake_run_phase(
        phase: QualityPhase,
        *,
        available_gates: dict[str, QualityGate],
    ) -> tools.run_quality_gates.PhaseResult:
        return tools.run_quality_gates.PhaseResult(
            phase=phase,
            gate_results=(
                tools.run_quality_gates.GateResult(
                    gate=available_gates["ruff"],
                    returncode=0,
                    stdout="",
                    stderr="",
                    elapsed=0.0,
                ),
            ),
        )

    monkeypatch.setattr(
        tools.run_quality_gates,
        "sync_pyright_config",
        fake_sync_pyright_config,
    )

    def fake_ensure_pyright_local_config() -> bool:
        calls.append("local")
        return False

    monkeypatch.setattr(
        tools.run_quality_gates,
        "ensure_pyright_local_config",
        fake_ensure_pyright_local_config,
    )
    monkeypatch.setattr(tools.run_quality_gates, "run_local_autofix", lambda: 0)
    monkeypatch.setattr(tools.run_quality_gates, "_phase_plan", fake_phase_plan)
    monkeypatch.setattr(tools.run_quality_gates, "_run_phase", fake_run_phase)

    assert tools.run_quality_gates.main(()) == 0

    assert calls == ["sync", "local"]


def test_quality_gates_aggregate_failures_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run_phase(
        phase: QualityPhase,
        *,
        available_gates: dict[str, QualityGate],
    ) -> tools.run_quality_gates.PhaseResult:
        calls.append(phase.name)
        gate_name = phase.gate_names[0]
        return tools.run_quality_gates.PhaseResult(
            phase=phase,
            gate_results=(
                tools.run_quality_gates.GateResult(
                    gate=available_gates[gate_name],
                    returncode=1 if phase.name == "all-at-once" else 0,
                    stdout="",
                    stderr="",
                    elapsed=0.0,
                ),
            ),
        )

    monkeypatch.setattr(tools.run_quality_gates, "sync_pyright_config", lambda: False)
    monkeypatch.setattr(
        tools.run_quality_gates, "ensure_pyright_local_config", lambda: False
    )
    monkeypatch.setattr(tools.run_quality_gates, "run_local_autofix", lambda: 0)
    monkeypatch.setattr(tools.run_quality_gates, "_run_phase", fake_run_phase)

    assert tools.run_quality_gates.main(()) == 1
    assert calls == ["all-at-once"]


def test_quality_gates_fail_fast_stops_after_first_failing_phase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run_phase(
        phase: QualityPhase,
        *,
        available_gates: dict[str, QualityGate],
    ) -> tools.run_quality_gates.PhaseResult:
        calls.append(phase.name)
        gate_name = phase.gate_names[0]
        return tools.run_quality_gates.PhaseResult(
            phase=phase,
            gate_results=(
                tools.run_quality_gates.GateResult(
                    gate=available_gates[gate_name],
                    returncode=1,
                    stdout="",
                    stderr="",
                    elapsed=0.0,
                ),
            ),
        )

    monkeypatch.setattr(tools.run_quality_gates, "sync_pyright_config", lambda: False)
    monkeypatch.setattr(
        tools.run_quality_gates, "ensure_pyright_local_config", lambda: False
    )
    monkeypatch.setattr(tools.run_quality_gates, "run_local_autofix", lambda: 0)
    monkeypatch.setattr(tools.run_quality_gates, "_run_phase", fake_run_phase)

    assert tools.run_quality_gates.main(("--fail-fast",)) == 1
    assert calls == ["all-at-once"]


def test_quality_gates_fail_when_generated_pyright_config_was_stale(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(tools.run_quality_gates, "sync_pyright_config", lambda: True)

    assert tools.run_quality_gates.main(()) == 1

    assert "pyrightconfig.tests.json was out of sync" in capsys.readouterr().out


def test_quality_gates_can_skip_local_autofix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(tools.run_quality_gates, "sync_pyright_config", lambda: False)
    monkeypatch.setattr(
        tools.run_quality_gates, "ensure_pyright_local_config", lambda: False
    )

    def fake_run_local_autofix() -> int:
        calls.append("autofix")
        return 0

    def fake_phase_plan(
        _run_request: tools.run_quality_gates._RunRequest,
    ) -> tuple[QualityPhase, ...]:
        return (QualityPhase(name="noop", gate_names=("ruff",)),)

    def fake_run_phase(
        phase: QualityPhase,
        *,
        available_gates: dict[str, QualityGate],
    ) -> tools.run_quality_gates.PhaseResult:
        return tools.run_quality_gates.PhaseResult(
            phase=phase,
            gate_results=(
                tools.run_quality_gates.GateResult(
                    gate=available_gates["ruff"],
                    returncode=0,
                    stdout="",
                    stderr="",
                    elapsed=0.0,
                ),
            ),
        )

    monkeypatch.setattr(
        tools.run_quality_gates,
        "run_local_autofix",
        fake_run_local_autofix,
    )
    monkeypatch.setattr(tools.run_quality_gates, "_phase_plan", fake_phase_plan)
    monkeypatch.setattr(tools.run_quality_gates, "_run_phase", fake_run_phase)

    assert tools.run_quality_gates.main(("--no-auto-fix",)) == 0
    assert calls == []
