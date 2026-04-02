from __future__ import annotations

import json
from pathlib import Path

from reportlab.pdfgen import canvas
from typer.testing import CliRunner

from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
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
            "file",
            "--output-adapter",
            "cointracking_csv",
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
    assert (normalized_dir / "normalization_reviews.csv").exists()
    assert (normalized_dir / "timezone_issues.csv").exists()


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
    assert (output_dir / "baseline_exchange_reconciliation.csv").exists()


def test_source_manifest_cli(tmp_path: Path) -> None:
    source_dir = tmp_path / "capture"
    source_dir.mkdir()
    (source_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    output_path = tmp_path / "manifest.csv"

    result = runner.invoke(
        app,
        [
            "source",
            "manifest",
            "--source-dir",
            str(source_dir),
            "--output",
            str(output_path),
        ],
    )

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["file_count"] == 1
    assert output_path.exists()


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
        app,
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
            str(normalized_dir),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert (tmp_path / "wallet_inventory_summary.json").exists()


def test_round_scaffold_cli(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    runner.invoke(app, ["workspace", "init", "--workspace-root", str(workspace_root)], catch_exceptions=False)

    result = runner.invoke(
        app,
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


def test_source_intake_plan_cli(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    result = runner.invoke(
        app,
        [
            "source",
            "intake",
            "plan",
            "--incoming-dir",
            str(incoming_dir),
            "--workspace-root",
            str(workspace_root),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert result.exit_code == 0
    assert (report_dir / "intake_plan.csv").exists()


def test_source_intake_apply_cli(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    result = runner.invoke(
        app,
        [
            "source",
            "intake",
            "apply",
            "--incoming-dir",
            str(incoming_dir),
            "--workspace-root",
            str(workspace_root),
            "--report-dir",
            str(report_dir),
        ],
    )

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["copied_count"] == 1
    assert (report_dir / "intake_summary.json").exists()
    assert (workspace_root / "evidence/raw/source/unclassified/incoming/transactions.csv").exists()


def test_source_diff_cli(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.csv"
    reference_path = tmp_path / "reference.csv"
    candidate_path.write_text("Type,Date,Tx-ID\nTrade,2023-08-06 10:00:00,tx-1\n", encoding="utf-8")
    reference_path.write_text("Type,Date,Tx-ID\nTrade,2023-08-07 10:00:00,tx-2\n", encoding="utf-8")
    output_dir = tmp_path / "diff"

    result = runner.invoke(
        app,
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


def test_supporting_extract_pdf_balances_cli(tmp_path: Path) -> None:
    pdf_path = tmp_path / "shakepay_Performance report_2025.pdf"
    output_path = tmp_path / "balances.csv"
    pdf = canvas.Canvas(str(pdf_path))
    pdf.drawString(72, 750, "Performance report For the year ending on December 31, 2025")
    pdf.drawString(72, 735, "For the year ($) Since account opening ($) $256.37 $0.00")
    pdf.drawString(72, 720, "Opening market value (as of 2025-01-01 00:00 EST)")
    pdf.drawString(72, 705, "Closing market value at year end $643.81")
    pdf.save()

    result = runner.invoke(
        app,
        [
            "supporting",
            "extract-pdf-balances",
            "--pdf",
            str(pdf_path),
            "--output",
            str(output_path),
        ],
    )

    rows = FilesystemArtifactStore().read_rows(output_path)

    assert result.exit_code == 0
    assert len(rows) == 2
    assert rows[0]["balance_kind"] == "opening_market_value"
    assert rows[1]["balance_kind"] == "closing_market_value"
