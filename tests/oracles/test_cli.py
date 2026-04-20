from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Protocol, cast

import pytest
from typer.testing import CliRunner

from tools.oracles import cli as oracle_cli

runner = CliRunner()


class HasWorkspaceRoot(Protocol):
    workspace_root: Path


def test_oracle_cli_registers_expected_command_groups() -> None:
    result = runner.invoke(oracle_cli.app, ["--help"])

    assert result.exit_code == 0
    for command in ("baseline", "batch", "round", "source", "verification"):
        assert command in result.stdout


def test_round_scaffold_uses_configured_root_when_option_is_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_root = tmp_path / "configured-workspace"
    seen: dict[str, Path] = {}

    class StubRoundScaffoldingService:
        def execute(self, request: object) -> object:
            workspace_root = cast(HasWorkspaceRoot, request).workspace_root
            seen["workspace_root"] = workspace_root
            return SimpleNamespace(
                workspace_root=workspace_root,
                round_dir=workspace_root / "working/verification/example",
                round_log_path=workspace_root / "outputs/logs/round_log.csv",
                readme_path=workspace_root / "working/verification/example/README.md",
                seeded=True,
            )

    def configured_root_stub() -> Path:
        return configured_root

    def round_scaffolding_service_stub() -> StubRoundScaffoldingService:
        return StubRoundScaffoldingService()

    monkeypatch.setattr(oracle_cli, "configured_workspace_root", configured_root_stub)
    monkeypatch.setattr(
        oracle_cli, "_round_scaffolding_service", round_scaffolding_service_stub
    )

    result = runner.invoke(
        oracle_cli.app,
        [
            "round",
            "scaffold",
            "--round-id",
            "post_import_fixture_01",
            "--phase",
            "post_import",
            "--source",
            "fixture",
        ],
    )

    assert result.exit_code == 0
    assert seen["workspace_root"] == configured_root


def test_baseline_validate_cli(baseline_export_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "baseline"

    result = runner.invoke(
        oracle_cli.app,
        [
            "baseline",
            "validate",
            "--export-dir",
            str(baseline_export_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "baseline_summary.json").exists()
    assert (output_dir / "baseline_exchange_reconciliation.csv").exists()


def test_verification_compare_cli(
    verification_previous_dir: Path,
    verification_current_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "verification"

    result = runner.invoke(
        oracle_cli.app,
        [
            "verification",
            "compare",
            "--previous-dir",
            str(verification_previous_dir),
            "--current-dir",
            str(verification_current_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "verification_summary.json").exists()


def test_batch_stage_cli(baseline_export_dir: Path, tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.csv"
    candidate_path.write_text(
        "Type,Buy,Cur.,Sell,Cur..1,Fee,Cur..2,Exchange,Group,Comment,Date,Tx-ID\n"
        "Trade,1.0,BTC,10.0,CAD,0.1,CAD,Fixture,,import,2023-08-06 10:00:00,tx-2\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "batch"

    result = runner.invoke(
        oracle_cli.app,
        [
            "batch",
            "stage",
            "--candidate",
            str(candidate_path),
            "--baseline-export-dir",
            str(baseline_export_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "stage_summary.json").exists()


def test_batch_screen_cli_returns_nonzero_for_blocked_candidates(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    candidate_path.write_text(
        "Type,Buy,Cur.,Sell,Cur..1,Fee,Cur..2,Exchange,Group,Comment,Date,Tx-ID\n"
        "Trade,1.0,BTC,10.0,CAD,0.1,CAD,Fixture,,import,,tx-2\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "screen"

    result = runner.invoke(
        oracle_cli.app,
        [
            "batch",
            "screen",
            "--candidate",
            str(candidate_path),
            "--baseline-export-dir",
            str(baseline_export_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 1
    assert (output_dir / "stage_issues.csv").exists()


def test_round_scaffold_cli(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.joinpath("outputs/logs").mkdir(parents=True)

    result = runner.invoke(
        oracle_cli.app,
        [
            "round",
            "scaffold",
            "--round-id",
            "post_import_fixture_01",
            "--phase",
            "post_import",
            "--source",
            "fixture",
            "--workspace-root",
            str(workspace_root),
        ],
    )

    assert result.exit_code == 0
    assert (workspace_root / "working/verification/post_import_fixture_01").exists()


def test_source_diff_cli(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.csv"
    reference_path = tmp_path / "reference.csv"
    candidate_path.write_text(
        "Type,Date,Tx-ID\nTrade,2023-08-06 10:00:00,tx-1\n", encoding="utf-8"
    )
    reference_path.write_text(
        "Type,Date,Tx-ID\nTrade,2023-08-07 10:00:00,tx-2\n", encoding="utf-8"
    )
    output_dir = tmp_path / "diff"

    result = runner.invoke(
        oracle_cli.app,
        [
            "source",
            "diff",
            "--candidate",
            str(candidate_path),
            "--reference",
            str(reference_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["candidate_only_count"] == 1
    assert (output_dir / "candidate_only.csv").exists()
    assert (output_dir / "reference_only.csv").exists()
