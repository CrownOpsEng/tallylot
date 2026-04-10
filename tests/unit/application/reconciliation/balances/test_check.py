from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.application.reconciliation import (
    BalanceCheckRequest,
    BalanceCheckWorkflow,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.locations import LocationKind
from tallylot.domain.reconciliation import BalanceConfirmation, BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository
from tallylot.ports.evidence import LocationInventoryRecord


def test_balance_check_workflow_writes_single_source_outputs(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    evidence_repo.write_balance_snapshots(
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
    evidence_repo.write_balance_evidence(
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

    response = BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")
    issue_rows = artifacts.read_rows(output_root / "reconciliation_issues.csv")
    summary = json.loads(
        (output_root / "balance_assertion_summary.json").read_text(encoding="utf-8")
    )
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.source_count == 1
    assert response.issue_source_count == 1
    assert assertion_rows[0]["status"] == "drift"
    assert issue_rows[0]["kind"] == "balance_drift"
    assert summary["assertion_count"] == 1
    assert summary["issue_count"] == 1
    assert check_summary_rows[0]["check_status"] == "issues"
    assert check_summary_rows[0]["max_assertion_date"] == "2025-12-31"


def test_balance_check_rejects_capture_normalized_roots(tmp_path: Path) -> None:
    input_root = tmp_path / "working" / "normalized" / "captures"
    output_root = tmp_path / "analysis"
    input_root.mkdir(parents=True)

    with pytest.raises(ValueError, match="assembled source datasets"):
        BalanceCheckWorkflow(
            FilesystemEvidenceRepository(),
            FilesystemArtifactStore(),
        ).execute(
            BalanceCheckRequest(
                input_root_ref=to_resource_ref(input_root),
                output_root_ref=to_resource_ref(output_root),
            )
        )


def test_balance_check_workflow_uses_per_source_output_dirs_for_batch_runs(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    input_root.mkdir()
    for source_name in ("clean-source", "issue-source"):
        (input_root / source_name).mkdir()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)

    evidence_repo.write_balance_snapshots(
        input_root / "clean-source" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("clean-source"),
                location_id=LocationId("clean-source"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    evidence_repo.write_balance_evidence(
        input_root / "clean-source" / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("clean-source"),
                location_id=LocationId("clean-source"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                evidence_ref="clean-source.csv",
            ),
        ),
    )
    evidence_repo.write_balance_snapshots(
        input_root / "issue-source" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("issue-source"),
                location_id=LocationId("issue-source"),
                instrument_id=InstrumentId("ETH"),
                quantity=Decimal("2.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    evidence_repo.write_balance_evidence(
        input_root / "issue-source" / "balance_evidence.csv",
        (),
    )

    response = BalanceCheckWorkflow(
        evidence_repo,
        FilesystemArtifactStore(),
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    rows = FilesystemArtifactStore().read_rows(
        output_root / "balance_check_summary.csv"
    )

    assert response.clean_source_count == 1
    assert response.issue_source_count == 1
    assert (output_root / "clean-source" / "balance_assertions.csv").exists()
    assert (output_root / "issue-source" / "reconciliation_issues.csv").exists()
    assert rows[0]["source"] == "clean-source"
    assert rows[1]["source"] == "issue-source"


def test_balance_check_workflow_uses_confirmations_when_evidence_is_absent(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
    input_root.mkdir()

    evidence_repo.write_balance_snapshots(
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
    evidence_repo.write_balance_confirmations(
        input_root / "balance_confirmations.csv",
        (
            BalanceConfirmation(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                confirmation_kind="manual_assertion",
                asserted_meaning="Operator asserted the runtime balance directly.",
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                reason="Needed for runtime reconciliation.",
            ),
        ),
    )

    response = BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.clean_source_count == 1
    assert assertion_rows[0]["reference_basis"] == "operator_confirmation"
    assert check_summary_rows[0]["latest_clean_checked_date"] == "2025-12-31"
    assert check_summary_rows[0]["latest_source_backed_checked_date"] == ""
    assert (
        check_summary_rows[0]["reference_basis_counts"]
        == '{"operator_confirmation": 1}'
    )


def test_balance_check_workflow_prefers_evidence_over_confirmation(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
    input_root.mkdir()

    evidence_repo.write_balance_snapshots(
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
    evidence_repo.write_balance_evidence(
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
    evidence_repo.write_balance_confirmations(
        input_root / "balance_confirmations.csv",
        (
            BalanceConfirmation(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("9.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                confirmation_kind="manual_assertion",
                asserted_meaning="Operator asserted a conflicting balance.",
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                reason="Needed for runtime reconciliation.",
            ),
        ),
    )

    BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert assertion_rows[0]["status"] == "matched"
    assert assertion_rows[0]["reference_basis"] == "source_backed_evidence"
    assert (
        check_summary_rows[0]["reference_basis_counts"]
        == '{"source_backed_evidence": 1}'
    )
    assert check_summary_rows[0]["latest_source_backed_checked_date"] == "2025-12-31"


def test_balance_check_workflow_rejects_output_inside_input_root(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    input_root.mkdir()
    (input_root / "balances.csv").write_text(
        "source,location_id,instrument_id,quantity,as_of_at,as_of_precision,balance_kind,notes\n",
        encoding="utf-8",
    )
    (input_root / "balance_evidence.csv").write_text(
        "source,location_id,instrument_id,quantity,as_of_at,as_of_precision,balance_kind,evidence_ref,notes\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="balance check output root must not be inside balance input root",
    ):
        BalanceCheckWorkflow(
            FilesystemEvidenceRepository(),
            FilesystemArtifactStore(),
        ).execute(
            BalanceCheckRequest(
                input_root_ref=to_resource_ref(input_root),
                output_root_ref=to_resource_ref(input_root / "analysis"),
            )
        )


def test_balance_check_workflow_writes_cross_source_corroboration_artifacts(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    normalized_identifier = "0x1111111111111111111111111111111111111111"

    _write_source_inputs(
        evidence_repo,
        source_root=input_root / "eth-ledger1",
        source_name="eth-ledger1",
        location_id="evm:ethereum:0x1111111111111111111111111111111111111111",
        normalized_identifier=normalized_identifier,
        confidence="high",
        balances=(
            _balance_snapshot(
                "eth-ledger1",
                "evm:ethereum:0x1111111111111111111111111111111111111111",
                "symbol:ETH@evm_explorer",
                "1.5",
                as_of,
            ),
            _balance_snapshot(
                "eth-ledger1",
                "evm:ethereum:0x1111111111111111111111111111111111111111",
                "symbol:USDT@evm_explorer",
                "10",
                as_of,
            ),
        ),
        evidence=(
            _balance_evidence(
                "eth-ledger1",
                "evm:ethereum:0x1111111111111111111111111111111111111111",
                "symbol:ETH@evm_explorer",
                "1.5",
                as_of,
                "eth-ledger1.csv",
            ),
            _balance_evidence(
                "eth-ledger1",
                "evm:ethereum:0x1111111111111111111111111111111111111111",
                "symbol:USDT@evm_explorer",
                "10",
                as_of,
                "eth-ledger1.csv",
            ),
        ),
    )
    _write_source_inputs(
        evidence_repo,
        source_root=input_root / "ledger-live-main",
        source_name="ledger-live-main",
        location_id="evm:ethereum:0x1111111111111111111111111111111111111111",
        normalized_identifier=normalized_identifier,
        confidence="high",
        balances=(
            _balance_snapshot(
                "ledger-live-main",
                "evm:ethereum:0x1111111111111111111111111111111111111111",
                "symbol:ETH@ledger_live",
                "1.5",
                as_of,
            ),
            _balance_snapshot(
                "ledger-live-main",
                "evm:ethereum:0x1111111111111111111111111111111111111111",
                "symbol:USDT@ledger_live",
                "11",
                as_of,
            ),
        ),
        evidence=(
            _balance_evidence(
                "ledger-live-main",
                "evm:ethereum:0x1111111111111111111111111111111111111111",
                "symbol:ETH@ledger_live",
                "1.5",
                as_of,
                "ledger-live-main.csv",
            ),
            _balance_evidence(
                "ledger-live-main",
                "evm:ethereum:0x1111111111111111111111111111111111111111",
                "symbol:USDT@ledger_live",
                "11",
                as_of,
                "ledger-live-main.csv",
            ),
        ),
    )

    BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    cross_source_rows = artifacts.read_rows(output_root / "cross_source_assertions.csv")
    cross_source_summary = json.loads(
        (output_root / "cross_source_summary.json").read_text(encoding="utf-8")
    )

    assert [row["status"] for row in cross_source_rows] == ["matched", "drift"]
    assert cross_source_rows[0]["left_source"] == "eth-ledger1"
    assert cross_source_rows[0]["right_source"] == "ledger-live-main"
    assert cross_source_rows[0]["instrument_id"] == "symbol:ETH"
    assert cross_source_rows[1]["instrument_id"] == "symbol:USDT"
    assert cross_source_rows[1]["quantity_difference"] == "-1"
    assert cross_source_summary["matched_count"] == 1
    assert cross_source_summary["drift_count"] == 1
    assert cross_source_summary["issue_count"] == 0


def test_balance_check_workflow_surfaces_cross_source_missing_right(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    normalized_identifier = "0x2222222222222222222222222222222222222222"

    _write_source_inputs(
        evidence_repo,
        source_root=input_root / "eth-ledger1",
        source_name="eth-ledger1",
        location_id="evm:ethereum:0x2222222222222222222222222222222222222222",
        normalized_identifier=normalized_identifier,
        confidence="high",
        balances=(
            _balance_snapshot(
                "eth-ledger1",
                "evm:ethereum:0x2222222222222222222222222222222222222222",
                "symbol:ETH@evm_explorer",
                "0.75",
                as_of,
            ),
        ),
        evidence=(
            _balance_evidence(
                "eth-ledger1",
                "evm:ethereum:0x2222222222222222222222222222222222222222",
                "symbol:ETH@evm_explorer",
                "0.75",
                as_of,
                "eth-ledger1.csv",
            ),
        ),
    )
    _write_source_inputs(
        evidence_repo,
        source_root=input_root / "ledger-live-main",
        source_name="ledger-live-main",
        location_id="evm:ethereum:0x2222222222222222222222222222222222222222",
        normalized_identifier=normalized_identifier,
        confidence="high",
        balances=(),
        evidence=(),
    )

    BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    cross_source_rows = artifacts.read_rows(output_root / "cross_source_assertions.csv")
    cross_source_summary = json.loads(
        (output_root / "cross_source_summary.json").read_text(encoding="utf-8")
    )

    assert len(cross_source_rows) == 1
    assert cross_source_rows[0]["status"] == "missing_right"
    assert cross_source_summary["missing_right_count"] == 1


def test_balance_check_workflow_skips_low_confidence_cross_source_identity(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    normalized_identifier = "0x3333333333333333333333333333333333333333"

    _write_source_inputs(
        evidence_repo,
        source_root=input_root / "eth-ledger1",
        source_name="eth-ledger1",
        location_id="evm:ethereum:0x3333333333333333333333333333333333333333",
        normalized_identifier=normalized_identifier,
        confidence="high",
        balances=(
            _balance_snapshot(
                "eth-ledger1",
                "evm:ethereum:0x3333333333333333333333333333333333333333",
                "symbol:ETH@evm_explorer",
                "2",
                as_of,
            ),
        ),
        evidence=(
            _balance_evidence(
                "eth-ledger1",
                "evm:ethereum:0x3333333333333333333333333333333333333333",
                "symbol:ETH@evm_explorer",
                "2",
                as_of,
                "eth-ledger1.csv",
            ),
        ),
    )
    _write_source_inputs(
        evidence_repo,
        source_root=input_root / "ledger-live-main",
        source_name="ledger-live-main",
        location_id="evm:ethereum:0x3333333333333333333333333333333333333333",
        normalized_identifier=normalized_identifier,
        confidence="medium",
        balances=(
            _balance_snapshot(
                "ledger-live-main",
                "evm:ethereum:0x3333333333333333333333333333333333333333",
                "symbol:ETH@evm_explorer",
                "2",
                as_of,
            ),
        ),
        evidence=(
            _balance_evidence(
                "ledger-live-main",
                "evm:ethereum:0x3333333333333333333333333333333333333333",
                "symbol:ETH@evm_explorer",
                "2",
                as_of,
                "ledger-live-main.csv",
            ),
        ),
    )

    BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = artifacts.read_rows(output_root / "cross_source_issues.csv")
    cross_source_summary = json.loads(
        (output_root / "cross_source_summary.json").read_text(encoding="utf-8")
    )

    assert not artifacts.read_rows(output_root / "cross_source_assertions.csv")
    assert any(
        row["kind"] == "cross_source_low_confidence_identity" for row in issue_rows
    )
    assert cross_source_summary["skipped_count"] == 1


def test_balance_check_workflow_surfaces_cross_source_ambiguous_identity(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    normalized_identifier = "0x4444444444444444444444444444444444444444"

    _write_source_inputs(
        evidence_repo,
        source_root=input_root / "eth-ledger1",
        source_name="eth-ledger1",
        location_id="evm:ethereum:0x4444444444444444444444444444444444444444",
        normalized_identifier=normalized_identifier,
        confidence="high",
        balances=(
            _balance_snapshot(
                "eth-ledger1",
                "evm:ethereum:0x4444444444444444444444444444444444444444",
                "symbol:ETH@evm_explorer",
                "1",
                as_of,
            ),
        ),
        evidence=(
            _balance_evidence(
                "eth-ledger1",
                "evm:ethereum:0x4444444444444444444444444444444444444444",
                "symbol:ETH@evm_explorer",
                "1",
                as_of,
                "eth-ledger1.csv",
            ),
        ),
    )
    extra_root = input_root / "ledger-live-main"
    extra_root.mkdir(parents=True)
    evidence_repo.write_balance_snapshots(
        extra_root / "balances.csv",
        (
            _balance_snapshot(
                "ledger-live-main",
                "evm:ethereum:0x4444444444444444444444444444444444444444",
                "symbol:ETH@evm_explorer",
                "1",
                as_of,
            ),
            _balance_snapshot(
                "ledger-live-main",
                "evm:ethereum:0x4444444444444444444444444444444444444444:alt",
                "symbol:ETH@evm_explorer",
                "1",
                as_of,
            ),
        ),
    )
    evidence_repo.write_balance_evidence(
        extra_root / "balance_evidence.csv",
        (
            _balance_evidence(
                "ledger-live-main",
                "evm:ethereum:0x4444444444444444444444444444444444444444",
                "symbol:ETH@evm_explorer",
                "1",
                as_of,
                "ledger-live-main.csv",
            ),
            _balance_evidence(
                "ledger-live-main",
                "evm:ethereum:0x4444444444444444444444444444444444444444:alt",
                "symbol:ETH@evm_explorer",
                "1",
                as_of,
                "ledger-live-main.csv",
            ),
        ),
    )
    evidence_repo.write_location_inventory(
        extra_root / "location_inventory.csv",
        (
            _location_inventory_record(
                "ledger-live-main",
                "evm:ethereum:0x4444444444444444444444444444444444444444",
                normalized_identifier,
                "high",
            ),
            _location_inventory_record(
                "ledger-live-main",
                "evm:ethereum:0x4444444444444444444444444444444444444444:alt",
                normalized_identifier,
                "high",
            ),
        ),
    )

    BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = artifacts.read_rows(output_root / "cross_source_issues.csv")
    cross_source_summary = json.loads(
        (output_root / "cross_source_summary.json").read_text(encoding="utf-8")
    )

    assert not artifacts.read_rows(output_root / "cross_source_assertions.csv")
    assert any(row["kind"] == "cross_source_ambiguous_identity" for row in issue_rows)
    assert cross_source_summary["ambiguous_count"] == 1


def test_balance_check_workflow_dedupes_repeated_location_inventory_rows(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "normalized"
    output_root = tmp_path / "analysis"
    evidence_repo = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    normalized_identifier = "0x5555555555555555555555555555555555555555"

    _write_source_inputs(
        evidence_repo,
        source_root=input_root / "eth-ledger1",
        source_name="eth-ledger1",
        location_id="evm:ethereum:0x5555555555555555555555555555555555555555",
        normalized_identifier=normalized_identifier,
        confidence="high",
        balances=(
            _balance_snapshot(
                "eth-ledger1",
                "evm:ethereum:0x5555555555555555555555555555555555555555",
                "symbol:ETH@evm_explorer",
                "1",
                as_of,
            ),
        ),
        evidence=(
            _balance_evidence(
                "eth-ledger1",
                "evm:ethereum:0x5555555555555555555555555555555555555555",
                "symbol:ETH@evm_explorer",
                "1",
                as_of,
                "eth-ledger1.csv",
            ),
        ),
    )
    duplicate_root = input_root / "ledger-live-main"
    duplicate_root.mkdir(parents=True)
    evidence_repo.write_balance_snapshots(
        duplicate_root / "balances.csv",
        (
            _balance_snapshot(
                "ledger-live-main",
                "ledger_live_main:ethereum_1",
                "symbol:ETH@ledger_live",
                "1",
                as_of,
            ),
        ),
    )
    evidence_repo.write_balance_evidence(
        duplicate_root / "balance_evidence.csv",
        (
            _balance_evidence(
                "ledger-live-main",
                "ledger_live_main:ethereum_1",
                "symbol:ETH@ledger_live",
                "1",
                as_of,
                "ledger-live-main.csv",
            ),
        ),
    )
    repeated_record = _location_inventory_record(
        "ledger-live-main",
        "ledger_live_main:ethereum_1",
        normalized_identifier,
        "high",
    )
    evidence_repo.write_location_inventory(
        duplicate_root / "location_inventory.csv",
        (repeated_record, repeated_record),
    )

    BalanceCheckWorkflow(evidence_repo, artifacts).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    cross_source_rows = artifacts.read_rows(output_root / "cross_source_assertions.csv")
    cross_source_summary = json.loads(
        (output_root / "cross_source_summary.json").read_text(encoding="utf-8")
    )

    assert len(cross_source_rows) == 1
    assert cross_source_rows[0]["status"] == "matched"
    assert cross_source_rows[0]["instrument_id"] == "symbol:ETH"
    assert cross_source_summary["ambiguous_count"] == 0


def _write_source_inputs(
    evidence_repo: FilesystemEvidenceRepository,
    *,
    source_root: Path,
    source_name: str,
    location_id: str,
    normalized_identifier: str,
    confidence: str,
    balances: tuple[BalanceSnapshot, ...],
    evidence: tuple[BalanceEvidence, ...],
) -> None:
    source_root.mkdir(parents=True)
    evidence_repo.write_balance_snapshots(source_root / "balances.csv", balances)
    evidence_repo.write_balance_evidence(source_root / "balance_evidence.csv", evidence)
    evidence_repo.write_location_inventory(
        source_root / "location_inventory.csv",
        (
            _location_inventory_record(
                source_name,
                location_id,
                normalized_identifier,
                confidence,
            ),
        ),
    )


def _balance_snapshot(
    source: str,
    location_id: str,
    instrument_id: str,
    quantity: str,
    as_of: datetime,
) -> BalanceSnapshot:
    return BalanceSnapshot(
        source=SourceId(source),
        location_id=LocationId(location_id),
        instrument_id=InstrumentId(instrument_id),
        quantity=Decimal(quantity),
        as_of_at=as_of,
        as_of_precision=TemporalPrecision.DATE,
    )


def _balance_evidence(
    source: str,
    location_id: str,
    instrument_id: str,
    quantity: str,
    as_of: datetime,
    evidence_ref: str,
) -> BalanceEvidence:
    return BalanceEvidence(
        source=SourceId(source),
        location_id=LocationId(location_id),
        instrument_id=InstrumentId(instrument_id),
        quantity=Decimal(quantity),
        as_of_at=as_of,
        as_of_precision=TemporalPrecision.DATE,
        evidence_ref=evidence_ref,
    )


def _location_inventory_record(
    source: str,
    location_id: str,
    normalized_identifier: str,
    confidence: str,
) -> LocationInventoryRecord:
    return LocationInventoryRecord(
        source=source,
        location_id=LocationId(location_id),
        location_kind=LocationKind.ADDRESS,
        location_label=normalized_identifier,
        identifier_kind="evm_address",
        identifier_value=normalized_identifier,
        normalized_identifier=normalized_identifier,
        display_identifier=normalized_identifier,
        network_scope="ethereum",
        confidence=confidence,
        evidence_kind="filename",
        evidence_path="transactions.csv",
    )
