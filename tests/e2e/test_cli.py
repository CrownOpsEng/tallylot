from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from reportlab.pdfgen import canvas
from typer.testing import CliRunner

from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
from tallylot.application.capture_paths import default_capture_normalized_root
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    AccountingIntentHint,
    EconomicKind,
    EconomicLeg,
    FactSemantics,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, LocationId, SourceId, TransactionId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import (
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
)
from tallylot.interfaces.cli import app
from tallylot.ports.captures import SOURCE_CAPTURE_HEADER, SOURCE_INVENTORY_HEADER
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


def test_source_profile_cli_defaults_output_dir_to_capture_root_neighbor(
    structured_source_dir: Path, tmp_path: Path
) -> None:
    raw_capture_root = materialize_capture_root(
        tmp_path, source="fixture_source", source_dir=structured_source_dir
    )
    expected_output_dir = default_capture_normalized_root(raw_capture_root)

    result = runner.invoke(
        app,
        [
            "source",
            "profile",
            "--source",
            "fixture_source",
            "--raw-dir",
            str(raw_capture_root),
        ],
    )

    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["profile_output_ref"] == str(expected_output_dir)
    assert (expected_output_dir / "profile.json").exists()
    assert (expected_output_dir / "profile_inventory.csv").exists()


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


def test_source_normalize_cli_writes_translation_planner_artifacts_for_coinbase(
    tmp_path: Path,
) -> None:
    raw_capture_root = materialize_capture_root(tmp_path, source="coinbase")
    older_name = "2021 Statement.csv"
    newer_name = "2026-03-23 Statement - All Time.csv"
    (raw_capture_root / older_name).write_text(
        _coinbase_older_retail_csv(),
        encoding="utf-8",
    )
    (raw_capture_root / newer_name).write_text(
        _coinbase_newer_all_time_retail_csv(),
        encoding="utf-8",
    )
    output_dir = tmp_path / "normalized"

    result = runner.invoke(
        app,
        [
            "source",
            "normalize",
            "--source",
            "coinbase",
            "--raw-dir",
            str(raw_capture_root),
            "--output-dir",
            str(output_dir),
        ],
    )
    candidates = json.loads(
        (output_dir / "translation_input_candidates.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (output_dir / "translation_input_plan.json").read_text(encoding="utf-8")
    )

    assert result.exit_code == 0
    assert {candidate["candidate_id"] for candidate in candidates["candidates"]} == {
        f"coinbase:retail_export:{older_name}",
        f"coinbase:retail_export:{newer_name}",
    }
    assert plan["selected_candidate_ids"] == [f"coinbase:retail_export:{newer_name}"]
    assert (output_dir / "facts.csv").exists()


def test_source_normalize_cli_returns_nonzero_for_blocked_coinbase_plan(
    tmp_path: Path,
) -> None:
    raw_capture_root = materialize_capture_root(tmp_path, source="coinbase")
    (raw_capture_root / "2021 statement a.csv").write_text(
        _coinbase_retail_csv_with_amount("tx-a", "1.00000000"),
        encoding="utf-8",
    )
    (raw_capture_root / "2021 statement b.csv").write_text(
        _coinbase_retail_csv_with_amount("tx-b", "2.00000000"),
        encoding="utf-8",
    )
    output_dir = tmp_path / "normalized"

    result = runner.invoke(
        app,
        [
            "source",
            "normalize",
            "--source",
            "coinbase",
            "--raw-dir",
            str(raw_capture_root),
            "--output-dir",
            str(output_dir),
        ],
    )
    plan = json.loads(
        (output_dir / "translation_input_plan.json").read_text(encoding="utf-8")
    )

    assert result.exit_code == 2
    assert "translation input planning blocked normalization" in result.stdout
    assert plan["blocked"] is True
    assert not (output_dir / "facts.csv").exists()


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
        capture_root / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=BalanceTarget(
                    source=SourceId("coinbase"),
                    location_id=LocationId("coinbase:primary"),
                    instrument_id=InstrumentId("symbol:BTC@coinbase"),
                    balance_kind="available",
                    target_at=as_of,
                    target_precision=TemporalPrecision.DATE,
                ),
                quantity=Decimal("1.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    FilesystemEvidenceRepository().write_balance_references(
        capture_root / "balance_references.csv",
        (
            BalanceReference(
                target=BalanceTarget(
                    source=SourceId("coinbase"),
                    location_id=LocationId("coinbase:primary"),
                    instrument_id=InstrumentId("symbol:BTC@coinbase"),
                    balance_kind="available",
                    target_at=as_of,
                    target_precision=TemporalPrecision.DATE,
                ),
                quantity=Decimal("1.0"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=as_of,
                observed_precision=TemporalPrecision.DATE,
                support_ref="statement.pdf#page=1",
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
    assert FilesystemArtifactStore().read_rows(
        assembled_root / "balance_references.csv"
    )


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


def test_source_intake_cli_reports_mixed_source_capture_as_ambiguous(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        workspace_root / "analysis" / "issues" / "source_inventory.csv",
        SOURCE_INVENTORY_HEADER,
        (
            {
                "source": "binance-main",
                "activity_after_cutoff": "",
                "scope_status": "",
                "status": "",
                "capture_count": "",
                "latest_capture_uid": "",
                "latest_capture_label": "",
                "latest_capture_completed_at": "",
                "assembly_status": "",
                "assembled_root_ref": "",
                "adapter_hints": "",
                "notes": "",
            },
            {
                "source": "coinbase-main",
                "activity_after_cutoff": "",
                "scope_status": "",
                "status": "",
                "capture_count": "",
                "latest_capture_uid": "",
                "latest_capture_label": "",
                "latest_capture_completed_at": "",
                "assembly_status": "",
                "assembled_root_ref": "",
                "adapter_hints": "",
                "notes": "",
            },
        ),
    )
    artifacts.write_rows(
        workspace_root / "analysis" / "issues" / "source_label_map.csv",
        ("incoming_capture_scope", "incoming_path_prefix", "source", "notes"),
        (
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": "binance",
                "source": "binance-main",
                "notes": "",
            },
            {
                "incoming_capture_scope": "",
                "incoming_path_prefix": "coinbase",
                "source": "coinbase-main",
                "notes": "",
            },
        ),
    )
    incoming_dir = tmp_path / "incoming"
    (incoming_dir / "binance").mkdir(parents=True)
    (incoming_dir / "coinbase").mkdir(parents=True)
    (incoming_dir / "binance" / "transactions.csv").write_text(
        "a,b\n1,2\n", encoding="utf-8"
    )
    (incoming_dir / "coinbase" / "transactions.csv").write_text(
        "a,b\n3,4\n", encoding="utf-8"
    )
    (incoming_dir / "binance" / "notes.png").write_bytes(b"support")
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
    plan_rows = artifacts.read_rows(report_dir / "intake_plan.csv")
    support_row = next(
        row for row in plan_rows if row["relative_path"] == "binance/notes.png"
    )
    source_row = next(
        row for row in plan_rows if row["relative_path"] == "binance/transactions.csv"
    )
    support_target = Path(support_row["target_path"])

    assert result.exit_code == 1
    assert payload["source"] == ""
    assert payload["capture_status"] == "capture_blocked"
    assert payload["copied_count"] == 1
    assert support_row["action"] == "copy"
    assert source_row["capture_label"] == ""
    assert support_row["review_codes"] == "mixed_source_capture"
    assert support_target.exists()


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


def test_source_intake_cli_uses_nonzero_exit_for_overlap_review_capture(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    first_incoming = tmp_path / "incoming-1"
    second_incoming = tmp_path / "incoming-2"
    first_incoming.mkdir()
    second_incoming.mkdir()
    payload_a = (
        "Pair,Coin,Date,Amount,Type,Status\n"
        "ADA/USDT,USDT,2021-05-25 12:53:03,0.0345,Auto borrowing,CONFIRM\n"
    )
    payload_b = (
        "Pair,Coin,Date,Amount,Type,Status\n"
        "ADA/USDT,USDT,2021-05-25 12:53:03,0.0500,Auto borrowing,CONFIRM\n"
    )
    (first_incoming / "borrow.csv").write_text(payload_a, encoding="utf-8")
    (second_incoming / "borrow.csv").write_text(payload_b, encoding="utf-8")
    first_report_dir = tmp_path / "reports-1"
    second_report_dir = tmp_path / "reports-2"

    first_result = runner.invoke(
        app,
        [
            "source",
            "intake",
            "apply",
            "--incoming-dir",
            str(first_incoming),
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
            str(second_incoming),
            "--workspace-root",
            str(workspace_root),
            "--report-dir",
            str(second_report_dir),
        ],
    )

    payload = json.loads(second_result.stdout)

    assert first_result.exit_code == 0
    assert second_result.exit_code == 1
    assert payload["source"] == "binance"
    assert payload["capture_status"] == "overlap_review_required"
    assert payload["capture_label"] != ""
    assert payload["copied_count"] == 1
    assert (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "binance"
        / payload["capture_label"]
        / "borrow.csv"
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
    assert (submission_root / "balance_snapshots.csv.example").exists()
    assert (submission_root / "balance_references.csv.example").exists()
    assert not (submission_root / "balance_snapshots.csv").exists()
    assert not (submission_root / "balance_references.csv").exists()


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
    assert payload["ready_for_balance_check"] is True
    assert payload["wrote_balance_snapshots"] is True
    assert payload["wrote_balance_references"] is True
    assert (output_root / "balance_snapshots.csv").exists()
    assert (output_root / "balance_references.csv").exists()
    assert (output_root / "balance_submission_summary.json").exists()


def test_checkpoint_submit_balances_cli_blocks_when_required_file_missing(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "supporting" / "coinbase"
    output_root = tmp_path / "normalized" / "coinbase"
    FilesystemArtifactStore().write_rows(
        submission_root / "balance_snapshots.csv",
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "target_at",
            "target_precision",
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
                "target_at": "2026-03-23",
                "target_precision": "date",
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
    (submission_root / "balance_snapshots.csv").write_text(
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
    FilesystemFactRepository().write_facts(
        normalized_root / "facts.csv",
        (
            _fact(
                source="coinbase",
                instrument_id="symbol:BTC@coinbase",
                quantity="1.25",
                as_of=datetime(2026, 3, 23, tzinfo=UTC),
                location_id="coinbase:primary",
            ),
        ),
    )

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
            "--as-of",
            "2026-03-23",
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
    inspect_path = tmp_path / "balance_inspect.csv"
    summary_path = tmp_path / "balance_reconciliation_summary.json"
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
    input_root.mkdir()

    FilesystemFactRepository().write_facts(
        input_root / "facts.csv",
        (
            _fact(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                as_of=as_of,
                location_id="coinbase",
            ),
        ),
    )
    FilesystemEvidenceRepository().write_balance_snapshots(
        input_root / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=BalanceTarget(
                    source=SourceId("coinbase"),
                    location_id=LocationId("coinbase"),
                    instrument_id=InstrumentId("BTC"),
                    balance_kind="available",
                    target_at=as_of,
                    target_precision=TemporalPrecision.TIMESTAMP,
                ),
                quantity=Decimal("1.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    FilesystemEvidenceRepository().write_balance_references(
        input_root / "balance_references.csv",
        (
            BalanceReference(
                target=BalanceTarget(
                    source=SourceId("coinbase"),
                    location_id=LocationId("coinbase"),
                    instrument_id=InstrumentId("BTC"),
                    balance_kind="available",
                    target_at=as_of,
                    target_precision=TemporalPrecision.TIMESTAMP,
                ),
                quantity=Decimal("1.5"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=as_of,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref="statement.pdf#page=1",
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
            str(inspect_path),
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
            "--inspect",
            str(inspect_path),
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
        (analysis_root / "balance_reconciliation_summary.json").read_text(
            encoding="utf-8"
        )
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
        input_root / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=BalanceTarget(
                    source=SourceId("coinbase"),
                    location_id=LocationId("coinbase"),
                    instrument_id=InstrumentId("BTC"),
                    balance_kind="available",
                    target_at=as_of,
                    target_precision=TemporalPrecision.TIMESTAMP,
                ),
                quantity=Decimal("1.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )
    FilesystemEvidenceRepository().write_balance_references(
        input_root / "balance_references.csv",
        (
            BalanceReference(
                target=BalanceTarget(
                    source=SourceId("coinbase"),
                    location_id=LocationId("coinbase"),
                    instrument_id=InstrumentId("BTC"),
                    balance_kind="available",
                    target_at=as_of,
                    target_precision=TemporalPrecision.TIMESTAMP,
                ),
                quantity=Decimal("1.0"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=as_of,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref="statement.pdf#page=1",
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
        submission_root / "balance_snapshots.csv",
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "target_at",
            "target_precision",
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
                "target_at": "2026-03-23",
                "target_precision": "date",
                "balance_kind": "available",
                "notes": "snapshot",
            },
        ),
    )
    artifacts.write_rows(
        submission_root / "balance_references.csv",
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "target_at",
            "target_precision",
            "balance_kind",
            "reference_kind",
            "observed_at",
            "observed_precision",
            "support_ref",
            "reviewed_by",
            "reviewed_at",
            "notes",
        ),
        (
            {
                "source": source,
                "account": "primary",
                "wallet": "primary",
                "instrument_id": f"symbol:BTC@{source}",
                "quantity": "1.25",
                "target_at": "2026-03-23",
                "target_precision": "date",
                "balance_kind": "available",
                "reference_kind": "operator_assertion",
                "observed_at": "2026-03-23",
                "observed_precision": "date",
                "support_ref": "statement.pdf#page=1",
                "reviewed_by": "operator@example.com",
                "reviewed_at": "2026-03-24 00:00:00",
                "notes": "confirmation",
            },
        ),
    )


def _coinbase_older_retail_csv() -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "legacy-1,2021-12-30 08:56:53 UTC,Receive,FET,1.9859001,CAD,$0.64,$1.27098,$1.27098,$0.00,"
        "Received 1.9859001 FET\n"
    )


def _coinbase_newer_all_time_retail_csv() -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "legacy-1,2021-12-30 08:56:53 UTC,Receive,FET,1.9859001,CAD,$0.64,$1.27098,$1.27098,$0.00,"
        "Received 1.9859001 FET\n"
        "reward-1,2023-03-18 01:28:49 UTC,Reward Income,ADA,0.000021,CAD,$0.48,$0.00,$0.00,$0.00,"
        "Received 0.000021 ADA from Coinbase Rewards\n"
        "migration-neg,2025-10-17 13:38:17 UTC,Asset Migration,MATIC,-1.65526374,CAD,$0.25,-$0.42,-$0.42,$0.00,\n"
        "migration-pos,2025-10-17 13:38:17 UTC,Asset Migration,POL,1.65526374,CAD,$0.25,$0.42,$0.42,$0.00,\n"
    )


def _coinbase_retail_csv_with_amount(transaction_id: str, amount: str) -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        f"{transaction_id},2021-12-30 08:56:53 UTC,Receive,FET,{amount},CAD,$0.64,$1.27098,$1.27098,$0.00,"
        "Received FET\n"
    )


def _fact(
    *,
    source: str,
    instrument_id: str,
    quantity: str,
    as_of: datetime,
    location_id: str,
) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId(f"{source}:{instrument_id}:{as_of.isoformat()}"),
        source=SourceId(source),
        adapter_id=AdapterId("structured_csv"),
        timestamp=as_of,
        location_id=LocationId(location_id),
        semantics=FactSemantics(
            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
            projection_hint=ProjectionHint.DEPOSIT,
            accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        ),
        legs=(
            EconomicLeg(
                leg_id="primary",
                kind=LegKind.PRIMARY,
                instrument_id=InstrumentId(instrument_id),
                quantity=Decimal(quantity),
            ),
        ),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
    )
