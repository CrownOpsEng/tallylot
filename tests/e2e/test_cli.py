from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from reportlab.pdfgen import canvas
from typer.testing import CliRunner

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository
from tallylot.interfaces.cli import app

runner = CliRunner()


def test_workspace_init_cli(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"

    result = runner.invoke(
        app, ["workspace", "init", "--workspace-root", str(workspace_root)]
    )

    assert result.exit_code == 0
    assert (workspace_root / "analysis/issues/issue_log.csv").exists()


def test_profile_normalize_and_render_cli(
    structured_source_dir: Path, tmp_path: Path
) -> None:
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
            "--facts",
            str(normalized_dir / "facts.csv"),
            "--output",
            str(rendered_path),
        ],
    )

    assert profile_result.exit_code == 0
    assert normalize_result.exit_code == 0
    assert render_result.exit_code == 0
    assert rendered_path.exists()
    assert (normalized_dir / "facts.csv").exists()
    assert (normalized_dir / "fact_annotations.json").exists()
    assert (normalized_dir / "normalization_reviews.csv").exists()


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


def test_checkpoint_location_inventory_rebuild_cli(
    structured_source_dir: Path, tmp_path: Path
) -> None:
    normalized_dir = tmp_path / "normalized"
    output_path = tmp_path / "location_inventory.csv"

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
            "checkpoint",
            "rebuild-location-inventory",
            "--normalized-root",
            str(normalized_dir),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()
    assert (tmp_path / "location_inventory_summary.json").exists()


def test_source_intake_plan_and_apply_cli(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    report_dir = tmp_path / "reports"

    plan_result = runner.invoke(
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
    apply_result = runner.invoke(
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

    payload = json.loads(apply_result.stdout)

    assert plan_result.exit_code == 0
    assert apply_result.exit_code == 0
    assert (report_dir / "intake_plan.csv").exists()
    assert payload["copied_count"] == 1
    assert (
        workspace_root / "evidence/raw/source/unclassified/incoming/transactions.csv"
    ).exists()


def test_checkpoint_extract_pdf_balances_cli(tmp_path: Path) -> None:
    pdf_path = tmp_path / "shakepay_Performance report_2025.pdf"
    output_path = tmp_path / "balances.csv"
    pdf = canvas.Canvas(str(pdf_path))
    pdf.drawString(
        72, 750, "Performance report For the year ending on December 31, 2025"
    )
    pdf.drawString(
        72,
        735,
        "Change in value of your account For the year ($) Since account opening ($)",
    )
    pdf.drawString(
        72,
        720,
        "Opening market value $256.37 $0.00 (as of 2025-01-01 00:00 EST)",
    )
    pdf.drawString(
        72,
        705,
        "Closing market value at year end $643.81 $643.81 (as of 2025-12-31 23:59 EST)",
    )
    pdf.save()

    result = runner.invoke(
        app,
        [
            "checkpoint",
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
    assert rows[0]["value_amount"] == "256.37"
    assert rows[1]["balance_kind"] == "closing_market_value"
    assert rows[1]["value_amount"] == "643.81"


def test_checkpoint_extract_pdf_balances_cli_monthly_statement(tmp_path: Path) -> None:
    pdf_path = tmp_path / "shakepay_2026-03.pdf"
    output_path = tmp_path / "balances.csv"
    pdf = canvas.Canvas(str(pdf_path))
    pdf.drawString(72, 750, "Monthly account statement")
    pdf.drawString(72, 735, "Balance summary (as of 2026-04-01 00:00 EDT)")
    pdf.drawString(
        72,
        720,
        "Asset Quantity* Market price (CA$) Market value (CA$)** Original cost (CA$)***",
    )
    pdf.drawString(72, 705, "Cash (CAD) 18.76 1.00 18.76 18.76")
    pdf.drawString(72, 690, "US Dollar (USD) 0.00 1.3911 0.00 0.00")
    pdf.drawString(72, 675, "Bitcoin (BTC) 0.00186458 94,692.31 176.56 261.71")
    pdf.drawString(72, 660, "Ethereum (ETH) 0.00020245 2,922.49 0.59 0.51")
    pdf.save()

    result = runner.invoke(
        app,
        [
            "checkpoint",
            "extract-pdf-balances",
            "--pdf",
            str(pdf_path),
            "--output",
            str(output_path),
        ],
    )

    rows = FilesystemArtifactStore().read_rows(output_path)

    assert result.exit_code == 0
    assert len(rows) == 4
    assert rows[0]["balance_kind"] == "available"
    assert rows[0]["asset"] == "CAD"
    assert rows[0]["quantity"] == "18.76"
    assert rows[0]["as_of"] == "2026-04-01 04:00:00"
    assert rows[-1]["asset"] == "ETH"
    assert rows[-1]["quantity"] == "0.00020245"


def test_reconciliation_balance_commands_write_artifacts(tmp_path: Path) -> None:
    input_root = tmp_path / "coinbase"
    analysis_root = tmp_path / "analysis"
    coverage_path = tmp_path / "balance_coverage.csv"
    summary_path = tmp_path / "balance_reconciliation_summary.json"
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
    input_root.mkdir()

    FilesystemEvidenceRepository().write_balance_snapshots(
        input_root / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
    )
    FilesystemEvidenceRepository().write_balance_evidence(
        input_root / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.5"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                evidence_ref="statement.pdf#page=1",
            ),
        ),
    )

    inspect_result = runner.invoke(
        app,
        [
            "reconciliation",
            "balances",
            "inspect",
            "--input-root",
            str(input_root),
            "--output",
            str(coverage_path),
        ],
    )
    check_result = runner.invoke(
        app,
        [
            "reconciliation",
            "balances",
            "check",
            "--input-root",
            str(input_root),
            "--output-root",
            str(analysis_root),
        ],
    )
    summarize_result = runner.invoke(
        app,
        [
            "reconciliation",
            "balances",
            "summarize",
            "--coverage",
            str(coverage_path),
            "--check-summary",
            str(analysis_root / "balance_check_summary.csv"),
            "--output",
            str(summary_path),
        ],
    )

    assertion_rows = FilesystemArtifactStore().read_rows(
        analysis_root / "balance_assertions.csv"
    )
    issue_rows = FilesystemArtifactStore().read_rows(
        analysis_root / "reconciliation_issues.csv"
    )
    assertion_summary = json.loads(
        (analysis_root / "balance_assertion_summary.json").read_text(encoding="utf-8")
    )
    reconciliation_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert inspect_result.exit_code == 0
    assert check_result.exit_code == 0
    assert summarize_result.exit_code == 0
    assert assertion_rows[0]["status"] == "drift"
    assert issue_rows[0]["kind"] == "balance_drift"
    assert assertion_summary["assertion_count"] == 1
    assert assertion_summary["issue_count"] == 1
    assert reconciliation_summary["latest_observed_assertion_date"] == "2025-12-31"


def test_reconciliation_balance_check_cli_rejects_output_inside_input_root(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
    input_root.mkdir()

    FilesystemEvidenceRepository().write_balance_snapshots(
        input_root / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
    )
    FilesystemEvidenceRepository().write_balance_evidence(
        input_root / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                evidence_ref="statement.pdf#page=1",
            ),
        ),
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
            str(input_root / "analysis"),
        ],
    )

    assert result.exit_code == 2
    assert "balance check output root must not be inside balance input" in result.stderr
    assert "Traceback" not in result.stdout + result.stderr
