from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from repo_support.paths import repo_root
from repo_support.pytest_commands import build_fast_pytest_command

QUALITY_GATE_ORDER = (
    "markdownlint",
    "actionlint",
    "ruff",
    "mypy",
    "pyright",
    "pylint",
    "pytest",
)
QUALITY_SCHEDULES = ("auto", "all-at-once", "phased")


@dataclass(frozen=True)
class QualityGate:
    name: str
    command: tuple[str, ...]
    coverage_gate: bool = False


@dataclass(frozen=True)
class QualityPhase:
    name: str
    gate_names: tuple[str, ...]


def available_quality_gates(*, full_tests: bool) -> dict[str, QualityGate]:
    pytest_command = (
        ("uv", "run", "pytest") if full_tests else build_fast_pytest_command()
    )
    return {
        "markdownlint": QualityGate(
            name="markdownlint",
            command=("uv", "run", "pre-commit", "run", "markdownlint", "--all-files"),
        ),
        "actionlint": QualityGate(
            name="actionlint",
            command=("uv", "run", "actionlint", "-color"),
        ),
        "ruff": QualityGate(name="ruff", command=("uv", "run", "ruff", "check", ".")),
        "mypy": QualityGate(name="mypy", command=("uv", "run", "mypy")),
        "pyright": QualityGate(name="pyright", command=("uv", "run", "pyright")),
        "pylint": QualityGate(
            name="pylint",
            command=("uv", "run", "python", "-m", "tools.run_pylint"),
        ),
        "pytest": QualityGate(
            name="pytest",
            command=pytest_command,
            coverage_gate=full_tests,
        ),
    }


def quality_phase_plan(
    *,
    full_tests: bool,
    schedule: str,
    selected_gate_names: Iterable[str] | None = None,
) -> tuple[QualityPhase, ...]:
    if schedule not in QUALITY_SCHEDULES:
        raise ValueError(f"unsupported quality schedule: {schedule}")

    resolved_schedule = schedule
    if schedule == "auto":
        resolved_schedule = "all-at-once" if full_tests else "phased"

    phases: tuple[QualityPhase, ...]
    if resolved_schedule == "all-at-once":
        phases = (QualityPhase(name="all-at-once", gate_names=QUALITY_GATE_ORDER),)
    else:
        phases = (
            QualityPhase(
                name="quick-static",
                gate_names=("markdownlint", "actionlint", "ruff", "mypy"),
            ),
            QualityPhase(
                name="heavy-static",
                gate_names=("pyright", "pylint"),
            ),
            QualityPhase(name="tests", gate_names=("pytest",)),
        )

    selected = None
    if selected_gate_names is not None:
        selected = set(selected_gate_names)

    filtered_phases: list[QualityPhase] = []
    for phase in phases:
        gate_names = tuple(
            gate_name
            for gate_name in phase.gate_names
            if selected is None or gate_name in selected
        )
        if gate_names:
            filtered_phases.append(QualityPhase(name=phase.name, gate_names=gate_names))
    return tuple(filtered_phases)


def apply_gate_environment(
    existing: Mapping[str, str],
    *,
    coverage_gate: bool,
    coverage_file: Path | None = None,
) -> dict[str, str]:
    environment = dict(existing)
    if not coverage_gate:
        return environment

    coverage_config = str(repo_root() / "pyproject.toml")
    existing_addopts = environment.get("PYTEST_ADDOPTS", "").strip()
    coverage_addopt = f"--cov-config={coverage_config}"
    if coverage_addopt not in existing_addopts.split():
        environment["PYTEST_ADDOPTS"] = f"{existing_addopts} {coverage_addopt}".strip()
    if coverage_file is not None:
        environment["COVERAGE_FILE"] = str(coverage_file)
    return environment
