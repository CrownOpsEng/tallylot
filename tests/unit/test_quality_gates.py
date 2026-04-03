from __future__ import annotations

from pathlib import Path

from tools.run_quality_gates import DEFAULT_TEST_COMMAND, FULL_TEST_COMMAND, _quality_gates

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_quality_gates_default_to_fast_commit_time_pytest() -> None:
    gates = _quality_gates(full_tests=False)

    assert [gate.name for gate in gates] == ["ruff", "mypy", "pyright", "pylint", "pytest"]
    assert gates[3].command == ("uv", "run", "python", "-m", "tools.run_pylint")
    assert gates[-1].command == DEFAULT_TEST_COMMAND


def test_quality_gates_can_switch_to_full_pytest() -> None:
    gates = _quality_gates(full_tests=True)

    assert gates[-1].command == FULL_TEST_COMMAND


def test_pre_commit_config_excludes_pylint_hook() -> None:
    config_text = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "id: pylint" not in config_text
    assert "name: pytest-fast" in config_text
