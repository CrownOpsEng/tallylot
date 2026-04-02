from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from crypto_reconciliation.interfaces.cli import app

runner = CliRunner()


def test_workspace_init_cli(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"

    result = runner.invoke(app, ["workspace", "init", "--workspace-root", str(workspace_root)])

    assert result.exit_code == 0
    assert (workspace_root / "analysis/issues/issue_log.csv").exists()


def test_profile_normalize_and_render_cli(structured_source_dir: Path, tmp_path: Path) -> None:
    normalized_dir = tmp_path / "normalized"
    rendered_path = tmp_path / "cointracking.csv"

    profile_result = runner.invoke(
        app,
        [
            "source",
            "profile",
            "--source",
            "fixture_source",
            "--raw-dir",
            str(structured_source_dir),
            "--output-dir",
            str(normalized_dir),
        ],
    )
    normalize_result = runner.invoke(
        app,
        [
            "source",
            "normalize",
            "--source",
            "fixture_source",
            "--raw-dir",
            str(structured_source_dir),
            "--output-dir",
            str(normalized_dir),
        ],
    )
    render_result = runner.invoke(
        app,
        [
            "output",
            "render",
            "cointracking",
            "--canonical-events",
            str(normalized_dir / "canonical_events.csv"),
            "--output",
            str(rendered_path),
        ],
    )

    assert profile_result.exit_code == 0
    assert normalize_result.exit_code == 0
    assert render_result.exit_code == 0
    assert rendered_path.exists()


def test_baseline_validate_cli(baseline_export_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "baseline"

    result = runner.invoke(
        app,
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


def test_verification_compare_cli(
    verification_previous_dir: Path,
    verification_current_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "verification"

    result = runner.invoke(
        app,
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
        app,
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


def test_wallet_inventory_rebuild_cli(structured_source_dir: Path, tmp_path: Path) -> None:
    normalized_dir = tmp_path / "normalized"
    output_path = tmp_path / "wallet_inventory.csv"

    runner.invoke(
        app,
        [
            "source",
            "normalize",
            "--source",
            "fixture_source",
            "--raw-dir",
            str(structured_source_dir),
            "--output-dir",
            str(normalized_dir),
        ],
        catch_exceptions=False,
    )
    result = runner.invoke(
        app,
        [
            "wallet",
            "inventory",
            "rebuild",
            "--normalized-root",
            str(tmp_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
