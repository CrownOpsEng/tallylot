from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from reportlab.pdfgen import canvas
from typer.testing import CliRunner

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository
from tallylot.interfaces.cli import app
from tallylot.ports.captures import SOURCE_CAPTURE_HEADER
from tallylot.ports.evidence import (
    ISSUE_HEADER,
    LOCATION_INVENTORY_HEADER,
    NORMALIZATION_REVIEW_HEADER,
)
from tallylot.ports.facts import FACT_HEADER
from repo_support.capture_roots import materialize_capture_root

runner = CliRunner()


def test_workspace_init_cli(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"

    result = runner.invoke(
        app, ["workspace", "init", "--workspace-root", str(workspace_root)]
    )

    assert result.exit_code == 0
    assert (workspace_root / "analysis/issues/issue_log.csv").exists()
    assert (workspace_root / "analysis/issues/source_label_map.csv").exists()


def test_profile_normalize_and_render_cli(
    structured_source_dir: Path, tmp_path: Path
) -> None:
    raw_capture_root = materialize_capture_root(
        tmp_path, source="fixture_source", source_dir=structured_source_dir
    )
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
            str(raw_capture_root),
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
            str(raw_capture_root),
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


def test_source_profile_cli_rejects_non_capture_root(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    result = runner.invoke(
        app,
        [
            "source",
            "profile",
            "--source",
            "fixture_source",
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(tmp_path / "profile"),
        ],
    )

    assert result.exit_code == 2
    assert "capture.json" in result.stdout


def test_source_normalize_cli_rejects_mismatched_capture_root(tmp_path: Path) -> None:
    raw_capture_root = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_capture_root / "capture.json").write_text(
        json.dumps(
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "other_source",
                "capture_label": "2026-03-23T14-15-16Z",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/other_source",
                "manifest_fingerprint": "manifest:fixture",
                "status": "captured",
                "notes": "",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "source",
            "normalize",
            "--source",
            "fixture_source",
            "--raw-dir",
            str(raw_capture_root),
            "--output-dir",
            str(tmp_path / "normalized"),
        ],
    )

    assert result.exit_code == 2
    assert "does not match requested source" in result.stdout


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
    raw_capture_root = materialize_capture_root(
        tmp_path, source="fixture_source", source_dir=structured_source_dir
    )
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
            str(raw_capture_root),
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
    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    capture_label = summary["planned_capture_label"]

    assert plan_result.exit_code == 0
    assert apply_result.exit_code == 0
    assert (report_dir / "intake_plan.csv").exists()
    assert payload["source"] == "unclassified"
    assert payload["capture_status"] == "captured"
    assert payload["capture_label"] == capture_label
    assert payload["copied_count"] == 1
    assert (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "unclassified"
        / capture_label
        / "transactions.csv"
    ).exists()


def test_source_assemble_cli_writes_assembled_source_dataset(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    capture_uid = "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    capture_root = workspace_root / "working" / "normalized" / "captures" / capture_uid
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    artifacts.write_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv",
        SOURCE_CAPTURE_HEADER,
        (
            {
                "capture_uid": capture_uid,
                "source": "coinbase",
                "capture_label": "2026-03-23T14-15-16Z",
                "status": "normalized",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/coinbase",
                "capture_root_ref": "evidence/raw/source/coinbase/2026-03-23T14-15-16Z",
                "manifest_fingerprint": "manifest:fixture",
                "file_count": "1",
                "observed_period_start": "2026-03-23",
                "observed_period_end": "2026-03-23",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
        ),
    )
    artifacts.write_rows(capture_root / "facts.csv", FACT_HEADER, ())
    artifacts.write_json(capture_root / "fact_annotations.json", [])
    FilesystemEvidenceRepository().write_balance_snapshots(
        capture_root / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase:primary"),
                instrument_id=InstrumentId("symbol:BTC@coinbase"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    FilesystemEvidenceRepository().write_balance_evidence(
        capture_root / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase:primary"),
                instrument_id=InstrumentId("symbol:BTC@coinbase"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
            ),
        ),
    )
    artifacts.write_rows(capture_root / "exceptions.csv", ISSUE_HEADER, ())
    artifacts.write_rows(
        capture_root / "normalization_reviews.csv",
        NORMALIZATION_REVIEW_HEADER,
        (),
    )
    artifacts.write_rows(
        capture_root / "location_inventory.csv",
        LOCATION_INVENTORY_HEADER,
        (),
    )

    result = runner.invoke(
        app,
        [
            "source",
            "assemble",
            "--source",
            "coinbase",
            "--workspace-root",
            str(workspace_root),
        ],
    )

    assembled_root = workspace_root / "working" / "normalized" / "sources" / "coinbase"

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["included_capture_count"] == 1
    assert (assembled_root / "assembly_summary.json").exists()
    assert FilesystemArtifactStore().read_rows(assembled_root / "balance_evidence.csv")


def test_source_intake_cli_uses_workspace_source_label_map(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    FilesystemArtifactStore().write_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv",
        ("source",),
        ({"source": "manual-main"},),
    )
    FilesystemArtifactStore().write_rows(
        workspace_root / "analysis" / "issues" / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": ".",
                "source": "manual-main",
                "notes": "",
            },
        ),
    )
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
    plan_rows = FilesystemArtifactStore().read_rows(report_dir / "intake_plan.csv")
    summary = json.loads(
        (report_dir / "intake_summary.json").read_text(encoding="utf-8")
    )
    capture_label = summary["planned_capture_label"]

    assert result.exit_code == 0
    assert payload["source"] == "manual-main"
    assert payload["capture_status"] == "captured"
    assert payload["capture_label"] == capture_label
    assert payload["copied_count"] == 1
    assert plan_rows[0]["source_resolution_status"] == "explicit_map"
    assert (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "manual-main"
        / capture_label
        / "transactions.csv"
    ).exists()


def test_source_intake_cli_reports_blocked_capture_status(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv",
        ("source",),
        ({"source": "manual-main"},),
    )
    artifacts.write_rows(
        workspace_root / "analysis" / "issues" / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": ".",
                "source": "missing-source",
                "notes": "",
            },
        ),
    )
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

    assert result.exit_code == 1
    assert payload["source"] == ""
    assert payload["capture_status"] == "capture_blocked"
    assert payload["capture_label"] == ""
    assert payload["copied_count"] == 0


def test_source_intake_cli_uses_nonzero_exit_for_duplicate_blocked_capture(
    tmp_path: Path,
) -> None:
    incoming_dir = tmp_path / "incoming"
    incoming_dir.mkdir()
    (incoming_dir / "transactions.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    workspace_root = tmp_path / "workspace"
    first_report_dir = tmp_path / "reports-1"
    second_report_dir = tmp_path / "reports-2"

    first_result = runner.invoke(
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
            str(first_report_dir),
        ],
    )
    second_result = runner.invoke(
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
            str(second_report_dir),
        ],
    )

    payload = json.loads(second_result.stdout)

    assert first_result.exit_code == 0
    assert second_result.exit_code == 1
    assert payload["source"] == "unclassified"
    assert payload["capture_status"] == "duplicate_blocked"
    assert payload["capture_label"] == ""
    assert payload["copied_count"] == 0


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


def test_checkpoint_scaffold_balance_submission_cli(tmp_path: Path) -> None:
    submission_root = tmp_path / "supporting" / "coinbase"

    result = runner.invoke(
        app,
        [
            "checkpoint",
            "scaffold-balance-submission",
            "--source",
            "coinbase",
            "--output-root",
            str(submission_root),
        ],
    )

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["source"] == "coinbase"
    assert (submission_root / "README.md").exists()
    assert (submission_root / "balances.csv.example").exists()
    assert not (submission_root / "balances.csv").exists()


def test_checkpoint_submit_balances_cli(tmp_path: Path) -> None:
    submission_root = tmp_path / "supporting" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_submission_rows(submission_root, source="coinbase")

    result = runner.invoke(
        app,
        [
            "checkpoint",
            "submit-balances",
            "--source",
            "coinbase",
            "--submission-root",
            str(submission_root),
            "--output-root",
            str(output_root),
        ],
    )

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["blocked"] is False
    assert payload["trust_tier"] == "operator_confirmed"
    assert (output_root / "balances.csv").exists()
    assert (output_root / "balance_confirmations.csv").exists()
    assert not (output_root / "balance_evidence.csv").exists()
    assert (output_root / "balance_submission_summary.json").exists()


def test_checkpoint_submit_balances_cli_blocks_when_required_file_missing(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "supporting" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    FilesystemArtifactStore().write_rows(
        submission_root / "balances.csv",
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
            "notes",
        ),
        (
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "instrument_id": "symbol:BTC@coinbase",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "notes": "",
            },
        ),
    )

    result = runner.invoke(
        app,
        [
            "checkpoint",
            "submit-balances",
            "--source",
            "coinbase",
            "--submission-root",
            str(submission_root),
            "--output-root",
            str(output_root),
        ],
    )

    payload = json.loads(result.stdout)
    issue_rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_submission_issues.csv"
    )

    assert result.exit_code == 0
    assert payload["blocked"] is True
    assert issue_rows[0]["issue_kind"] == "missing_required_file"


def test_checkpoint_submit_balances_cli_blocks_for_bad_header(tmp_path: Path) -> None:
    submission_root = tmp_path / "supporting" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    _write_submission_rows(submission_root, source="coinbase")
    (submission_root / "balances.csv").write_text(
        "source,wallet,instrument_id\ncoinbase,primary,symbol:BTC@coinbase\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "checkpoint",
            "submit-balances",
            "--source",
            "coinbase",
            "--submission-root",
            str(submission_root),
            "--output-root",
            str(output_root),
        ],
    )

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["blocked"] is True


def test_checkpoint_submit_balances_cli_writes_optional_location_inventory(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "supporting" / "ledger"
    output_root = tmp_path / "normalized" / "ledger"
    _write_submission_rows(submission_root, source="ledger")
    FilesystemArtifactStore().write_rows(
        submission_root / "location_inventory.csv",
        (
            "source",
            "account",
            "wallet",
            "identifier_kind",
            "identifier_value",
            "network_scope",
            "controller",
            "confidence",
            "notes",
        ),
        (
            {
                "source": "ledger",
                "account": "primary",
                "wallet": "wallet-1",
                "identifier_kind": "evm_address",
                "identifier_value": "0x1111111111111111111111111111111111111111",
                "network_scope": "ethereum",
                "controller": "self_custody",
                "confidence": "high",
                "notes": "",
            },
        ),
    )

    result = runner.invoke(
        app,
        [
            "checkpoint",
            "submit-balances",
            "--source",
            "ledger",
            "--submission-root",
            str(submission_root),
            "--output-root",
            str(output_root),
        ],
    )

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["wrote_location_inventory"] is True
    assert (output_root / "location_inventory.csv").exists()


def test_submitted_balance_output_can_be_checked_by_reconciliation_cli(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "supporting" / "coinbase"
    normalized_root = tmp_path / "normalized" / "coinbase"
    analysis_root = tmp_path / "analysis"
    _write_submission_rows(submission_root, source="coinbase")

    submit_result = runner.invoke(
        app,
        [
            "checkpoint",
            "submit-balances",
            "--source",
            "coinbase",
            "--submission-root",
            str(submission_root),
            "--output-root",
            str(normalized_root),
        ],
    )
    check_result = runner.invoke(
        app,
        [
            "reconciliation",
            "balances",
            "check",
            "--input-root",
            str(normalized_root),
            "--output-root",
            str(analysis_root),
        ],
    )

    payload = json.loads(check_result.stdout)

    assert submit_result.exit_code == 0
    assert check_result.exit_code == 0
    assert payload["clean_source_count"] == 1
    assert (analysis_root / "balance_assertions.csv").exists()


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
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
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
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
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


def _write_submission_rows(submission_root: Path, *, source: str) -> None:
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        submission_root / "balances.csv",
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
            "notes",
        ),
        (
            {
                "source": source,
                "account": "primary",
                "wallet": "primary",
                "instrument_id": f"symbol:BTC@{source}",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "notes": "snapshot",
            },
        ),
    )
    artifacts.write_rows(
        submission_root / "balance_confirmations.csv",
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
            "confirmation_kind",
            "support_ref",
            "asserted_meaning",
            "reviewed_by",
            "reviewed_at",
            "reason",
            "notes",
        ),
        (
            {
                "source": source,
                "account": "primary",
                "wallet": "primary",
                "instrument_id": f"symbol:BTC@{source}",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "confirmation_kind": "external_support",
                "support_ref": "statement.pdf#page=1",
                "asserted_meaning": "Closing balance from the cited statement.",
                "reviewed_by": "operator@example.com",
                "reviewed_at": "2026-03-24 00:00:00",
                "reason": "Needed for runtime reconciliation.",
                "notes": "confirmation",
            },
        ),
    )
