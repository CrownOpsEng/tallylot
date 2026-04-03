from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Protocol, cast

import pytest
from typer.testing import CliRunner

from tallylot.domain.types import WorkspacePath
from tallylot.interfaces.cli import app
from tallylot.interfaces.cli import reconciliation as cli_reconciliation
from tallylot.interfaces.cli import workspace as cli_workspace

runner = CliRunner()


class HasWorkspaceRoot(Protocol):
    workspace_root_ref: WorkspacePath


class HasBalanceAssertionRefs(Protocol):
    snapshot_input_ref: str
    evidence_input_ref: str
    assertion_output_ref: str


def test_cli_registers_current_command_groups() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in (
        "workspace",
        "source",
        "checkpoint",
        "reconciliation",
        "output",
    ):
        assert command in result.stdout
    for removed_command in (
        "baseline",
        "wallet",
        "verification",
        "batch",
        "round",
        "supporting",
    ):
        assert removed_command not in result.stdout


def test_workspace_init_uses_configured_root_when_option_is_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_root = tmp_path / "configured-workspace"
    seen: dict[str, WorkspacePath] = {}

    class StubWorkspaceUseCase:
        def execute(self, request: object) -> object:
            workspace_root = cast(HasWorkspaceRoot, request).workspace_root_ref
            seen["workspace_root"] = workspace_root
            return SimpleNamespace(
                workspace_root_ref=workspace_root, created_refs=("a", "b")
            )

    monkeypatch.setattr(
        cli_workspace, "configured_workspace_root", lambda: configured_root
    )
    monkeypatch.setattr(
        cli_workspace, "initialize_workspace_use_case", lambda: StubWorkspaceUseCase()
    )

    result = runner.invoke(app, ["workspace", "init"])

    assert result.exit_code == 0
    assert seen["workspace_root"] == str(configured_root)


def test_reconciliation_assert_balances_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshots_path = tmp_path / "balances.csv"
    evidence_path = tmp_path / "balance_evidence.csv"
    output_path = tmp_path / "balance_assertions.csv"
    seen: dict[str, object] = {}

    class StubAssertBalancesUseCase:
        def execute(self, request: object) -> object:
            seen["request"] = request
            return SimpleNamespace(
                assertion_output_ref=str(output_path),
                assertion_count=1,
                issue_count=0,
            )

    monkeypatch.setattr(
        cli_reconciliation,
        "assert_balances_use_case",
        lambda: StubAssertBalancesUseCase(),
    )

    result = runner.invoke(
        app,
        [
            "reconciliation",
            "assert-balances",
            "--snapshots",
            str(snapshots_path),
            "--evidence",
            str(evidence_path),
            "--output",
            str(output_path),
        ],
    )

    request = cast(HasBalanceAssertionRefs, seen["request"])

    assert result.exit_code == 0
    assert request.snapshot_input_ref == str(snapshots_path)
    assert request.evidence_input_ref == str(evidence_path)
    assert request.assertion_output_ref == str(output_path)
