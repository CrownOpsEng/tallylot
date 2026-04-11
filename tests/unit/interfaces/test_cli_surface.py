from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Protocol, cast

import pytest
from typer.testing import CliRunner

from tallylot.application.capture_paths import source_assembled_root
from tallylot.domain.types import WorkspacePath
from tallylot.interfaces.cli import app
from tallylot.interfaces.cli import checkpoint as cli_checkpoint
from tallylot.interfaces.cli import reconciliation as cli_reconciliation
from tallylot.interfaces.cli import workspace as cli_workspace

runner = CliRunner()


class HasWorkspaceRoot(Protocol):
    workspace_root_ref: WorkspacePath


class HasBalanceInspectRefs(Protocol):
    input_root_ref: str
    inspect_output_ref: str


class HasBalanceCheckRefs(Protocol):
    input_root_ref: str
    output_root_ref: str
    sources: tuple[str, ...]
    hydrate_missing_references: bool
    reference_policy: str


class HasBalanceSummaryRefs(Protocol):
    inspect_input_ref: str
    check_summary_input_ref: str
    summary_output_ref: str


class HasSubmitBalancesRefs(Protocol):
    source: str
    submission_root_ref: str
    output_root_ref: str


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


def test_checkpoint_submit_balances_uses_source_assembled_root_when_output_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_root = tmp_path / "configured-workspace"
    submission_root = (
        configured_root
        / "working"
        / "supporting_artifacts"
        / "balance_submissions"
        / "coinbase"
    )
    expected_output_root = source_assembled_root(configured_root, "coinbase")
    seen: dict[str, object] = {}

    class StubSubmitBalancesUseCase:
        def execute(self, request: object) -> object:
            seen["request"] = request
            return SimpleNamespace(
                submission_root_ref=cast(
                    HasSubmitBalancesRefs, request
                ).submission_root_ref,
                output_root_ref=cast(HasSubmitBalancesRefs, request).output_root_ref,
                balance_snapshot_row_count=1,
                balance_reference_row_count=1,
                location_inventory_row_count=0,
                issue_count=0,
                blocked=False,
                wrote_balance_snapshots=True,
                wrote_balance_references=True,
                wrote_location_inventory=False,
                ready_for_balance_check=True,
            )

    monkeypatch.setattr(
        cli_checkpoint, "configured_workspace_root", lambda: configured_root
    )
    monkeypatch.setattr(
        cli_checkpoint,
        "submit_balances_use_case",
        lambda: StubSubmitBalancesUseCase(),
    )

    result = runner.invoke(
        app,
        [
            "checkpoint",
            "submit-balances",
            "--source",
            "coinbase",
        ],
    )

    request = cast(HasSubmitBalancesRefs, seen["request"])

    assert result.exit_code == 0
    assert request.source == "coinbase"
    assert request.submission_root_ref == str(submission_root)
    assert request.output_root_ref == str(expected_output_root)


def test_reconciliation_balance_inspect_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root = tmp_path / "normalized"
    output_path = tmp_path / "balance_inspect.csv"
    seen: dict[str, object] = {}

    class StubBalanceInspectWorkflow:
        def execute(self, request: object) -> object:
            seen["request"] = request
            return SimpleNamespace(
                inspect_output_ref=str(output_path),
                inspect_summary_output_ref=str(
                    tmp_path / "balance_inspect_summary.json"
                ),
                source_count=1,
                comparable_source_count=1,
            )

    monkeypatch.setattr(
        cli_reconciliation,
        "balance_inspect_workflow",
        lambda: StubBalanceInspectWorkflow(),
    )

    result = runner.invoke(
        app,
        [
            "reconciliation",
            "balances",
            "inspect",
            "--input-root",
            str(input_root),
            "--output",
            str(output_path),
        ],
    )

    request = cast(HasBalanceInspectRefs, seen["request"])

    assert result.exit_code == 0
    assert request.input_root_ref == str(input_root)
    assert request.inspect_output_ref == str(output_path)


def test_reconciliation_balance_check_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_root = tmp_path / "normalized"
    output_root = tmp_path / "analysis"
    seen: dict[str, object] = {}

    class StubBalanceCheckWorkflow:
        def execute(self, request: object) -> object:
            seen["request"] = request
            return SimpleNamespace(
                output_root_ref=str(output_root),
                check_summary_output_ref=str(output_root / "balance_check_summary.csv"),
                source_count=1,
                clean_source_count=1,
                issue_source_count=0,
                failed_source_count=0,
                no_assertion_source_count=0,
            )

    monkeypatch.setattr(
        cli_reconciliation,
        "balance_check_workflow",
        lambda: StubBalanceCheckWorkflow(),
    )

    result = runner.invoke(
        app,
        [
            "reconciliation",
            "balances",
            "check",
            "--input-root",
            str(input_root),
            "--output-root",
            str(output_root),
            "--source",
            "coinbase",
            "--source",
            "shakepay",
        ],
    )

    request = cast(HasBalanceCheckRefs, seen["request"])

    assert result.exit_code == 0
    assert request.input_root_ref == str(input_root)
    assert request.output_root_ref == str(output_root)
    assert request.sources == ("coinbase", "shakepay")
    assert request.hydrate_missing_references is False
    assert request.reference_policy == "default"


def test_reconciliation_balance_summarize_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inspect_path = tmp_path / "balance_inspect.csv"
    check_summary_path = tmp_path / "balance_check_summary.csv"
    output_path = tmp_path / "balance_reconciliation_summary.json"
    seen: dict[str, object] = {}

    class StubBalanceSummaryWorkflow:
        def execute(self, request: object) -> object:
            seen["request"] = request
            return SimpleNamespace(
                summary_output_ref=str(output_path),
                blocker_output_ref=str(
                    tmp_path / "balance_reconciliation_blockers.csv"
                ),
                source_count=1,
                latest_portfolio_clean_date="",
                latest_clean_source_date="2026-03-23",
                latest_observed_assertion_date="2026-03-23",
            )

    monkeypatch.setattr(
        cli_reconciliation,
        "balance_summary_workflow",
        lambda: StubBalanceSummaryWorkflow(),
    )

    result = runner.invoke(
        app,
        [
            "reconciliation",
            "balances",
            "summarize",
            "--inspect",
            str(inspect_path),
            "--check-summary",
            str(check_summary_path),
            "--output",
            str(output_path),
        ],
    )

    request = cast(HasBalanceSummaryRefs, seen["request"])

    assert result.exit_code == 0
    assert request.inspect_input_ref == str(inspect_path)
    assert request.check_summary_input_ref == str(check_summary_path)
    assert request.summary_output_ref == str(output_path)
