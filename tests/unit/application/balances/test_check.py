from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.application.balances import (
    BalanceCheckRequest,
    BalanceCheckWorkflow,
)
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.location_identifiers import location_id_from_parts
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
from tallylot.domain.types import AdapterId, SourceId, TransactionId
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tallylot.infrastructure.storage import (
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
)
from tallylot.ports.balance_providers import BalanceProviderPort


def _fact(
    *,
    fact_id: str,
    source: str,
    timestamp: datetime,
    location_id: str,
    instrument_id: str,
    quantity: str,
) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId(fact_id),
        source=SourceId(source),
        adapter_id=AdapterId("structured_csv"),
        timestamp=timestamp,
        location_id=location_id_from_parts(location_id),
        semantics=FactSemantics(
            economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
            projection_hint=ProjectionHint.DEPOSIT,
            accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
            tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
        ),
        legs=(
            EconomicLeg(
                leg_id=f"{fact_id}_primary".replace("-", "_"),
                kind=LegKind.PRIMARY,
                instrument_id=InstrumentId(instrument_id),
                quantity=Decimal(quantity),
            ),
        ),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
    )


def _target(source: str, instrument_id: str, target_at: datetime) -> BalanceTarget:
    return BalanceTarget(
        source=SourceId(source),
        location_id=location_id_from_parts(source),
        instrument_id=InstrumentId(instrument_id),
        balance_kind="available",
        target_at=target_at,
        target_precision=TemporalPrecision.TIMESTAMP,
    )


def _reference(
    *,
    source: str,
    instrument_id: str,
    quantity: str,
    target_at: datetime,
    reference_kind: BalanceReferenceKind,
) -> BalanceReference:
    if reference_kind is BalanceReferenceKind.SOURCE_DOCUMENT:
        return BalanceReference(
            target=_target(source, instrument_id, target_at),
            quantity=Decimal(quantity),
            reference_kind=reference_kind,
            observed_at=target_at,
            observed_precision=TemporalPrecision.TIMESTAMP,
            support_ref="statement.pdf#page=1",
        )
    if reference_kind is BalanceReferenceKind.OPERATOR_ASSERTION:
        return BalanceReference(
            target=_target(source, instrument_id, target_at),
            quantity=Decimal(quantity),
            reference_kind=reference_kind,
            observed_at=target_at,
            observed_precision=TemporalPrecision.TIMESTAMP,
            reviewed_by="operator@example.com",
            reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    return BalanceReference(
        target=_target(source, instrument_id, target_at),
        quantity=Decimal(quantity),
        reference_kind=reference_kind,
        observed_at=target_at,
        observed_precision=TemporalPrecision.TIMESTAMP,
        provider_family="evm_json_rpc",
    )


def test_balance_check_workflow_writes_single_source_outputs(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.5",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    response = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")
    issue_rows = artifacts.read_rows(output_root / "reconciliation_issues.csv")
    summary = json.loads(
        (output_root / "balance_reconciliation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.source_count == 1
    assert response.issue_source_count == 1
    assert response.resolution_mode == "offline"
    assert assertion_rows[0]["status"] == "drift"
    assert assertion_rows[0]["selected_reference_kind"] == "source_document"
    assert issue_rows[0]["kind"] == "balance_drift"
    assert summary["assertion_count"] == 1
    assert summary["issue_count"] == 1
    assert check_summary_rows[0]["resolution_mode"] == "offline"
    assert check_summary_rows[0]["check_status"] == "issues"
    assert check_summary_rows[0]["max_assertion_date"] == "2025-12-31"


def test_balance_check_workflow_clears_stale_outputs_when_source_stops_runnable(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    workflow = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    )
    response = workflow.execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )
    (output_root / "balance_assertions.csv").write_text("stale\n", encoding="utf-8")
    (input_root / "facts.csv").unlink()

    response = workflow.execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assert response.source_count == 1
    assert response.not_runnable_source_count == 1
    assert not (output_root / "balance_assertions.csv").exists()
    assert not (output_root / "reconciliation_issues.csv").exists()
    assert (output_root / "balance_reconciliation_summary.json").exists()
    assert (output_root / "balance_check_summary.csv").exists()
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")
    assert check_summary_rows[0]["check_status"] == "not_runnable"
    assert check_summary_rows[0]["not_runnable_reason"] == "no_balance_inputs"


def test_balance_check_workflow_clears_stale_reference_issue_cache(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    workflow = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    )
    workflow.execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )
    evidence.write_issue_records(
        input_root / "balance_reference_issues.csv",
        (
            IssueRecord(
                issue_id="coinbase:balance_check:stale_issue",
                source="coinbase",
                adapter_id="balance_check",
                severity="medium",
                kind="stale_issue",
                message="stale issue",
            ),
        ),
    )

    response = workflow.execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assert response.source_count == 1
    assert response.not_runnable_source_count == 0
    assert not (input_root / "balance_reference_issues.csv").exists()


def test_balance_check_workflow_clears_stale_reference_issue_cache_when_source_stops_runnable(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
    input_root.mkdir()

    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
            _fact(
                fact_id="fact-2",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="ETH",
                quantity="2.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    workflow = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    )
    response = workflow.execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )
    assert (input_root / "balance_reference_issues.csv").exists()
    (input_root / "facts.csv").unlink()

    second_response = workflow.execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assert response.source_count == 1
    assert response.not_runnable_source_count == 0
    assert second_response.not_runnable_source_count == 1
    assert not (input_root / "balance_reference_issues.csv").exists()


def test_balance_check_workflow_emits_missing_balance_reference_in_offline_mode(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )

    response = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    issue_rows = artifacts.read_rows(output_root / "reconciliation_issues.csv")
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.source_count == 1
    assert response.issue_source_count == 1
    assert response.resolution_mode == "offline"
    assert [row["kind"] for row in issue_rows] == ["missing_balance_reference"]
    assert all(row["kind"] != "unsupported_balance_provider" for row in issue_rows)
    assert check_summary_rows[0]["check_status"] == "issues"
    assert check_summary_rows[0]["resolution_mode"] == "offline"


def test_balance_check_workflow_emits_unsupported_balance_provider_when_hydrated(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )

    class _UnsupportedBalanceProviderRegistry:
        providers: tuple[BalanceProviderPort, ...] = ()

        def provider_for_requests(self, requests: tuple[object, ...]) -> None:
            del requests
            return None

    response = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
        providers=_UnsupportedBalanceProviderRegistry(),
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
            hydrate_missing_references=True,
        )
    )

    issue_rows = artifacts.read_rows(output_root / "reconciliation_issues.csv")
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.source_count == 1
    assert response.issue_source_count == 1
    assert response.resolution_mode == "hydrated"
    assert [row["kind"] for row in issue_rows] == ["unsupported_balance_provider"]
    assert check_summary_rows[0]["check_status"] == "issues"
    assert check_summary_rows[0]["resolution_mode"] == "hydrated"


def test_balance_check_workflow_reports_no_balance_targets_for_manual_sources(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 30, tzinfo=UTC)

    evidence.write_balance_snapshots(
        input_root / "balance_snapshots.csv",
        (
            BalanceSnapshot(
                target=_target("coinbase", "BTC", as_of),
                quantity=Decimal("1.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
    )

    response = BalanceCheckWorkflow(
        facts=FilesystemFactRepository(),
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
            as_of_values=("2025-12-31",),
        )
    )

    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.source_count == 1
    assert response.no_balance_target_source_count == 1
    assert response.resolution_mode == "offline"
    assert check_summary_rows[0]["check_status"] == "no_balance_targets"
    assert check_summary_rows[0]["resolution_mode"] == "offline"
    assert check_summary_rows[0]["not_runnable_reason"] == ""


def test_balance_check_workflow_reports_not_runnable_for_empty_sources(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    evidence.write_balance_references(input_root / "balance_references.csv", ())

    response = BalanceCheckWorkflow(
        facts=FilesystemFactRepository(),
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.source_count == 1
    assert response.not_runnable_source_count == 1
    assert response.resolution_mode == "offline"
    assert check_summary_rows[0]["check_status"] == "not_runnable"
    assert check_summary_rows[0]["resolution_mode"] == "offline"
    assert check_summary_rows[0]["not_runnable_reason"] == "no_balance_inputs"


def test_balance_check_workflow_reports_failed_status_for_invalid_reference_policy(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    input_root.mkdir()
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    response = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
            reference_policy="bogus",
        )
    )

    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.source_count == 1
    assert response.failed_source_count == 1
    assert response.resolution_mode == "offline"
    assert check_summary_rows[0]["check_status"] == "failed"
    assert check_summary_rows[0]["resolution_mode"] == "offline"
    assert (
        "unsupported balance reference_policy" in check_summary_rows[0]["error_message"]
    )


def test_balance_check_rejects_capture_normalized_roots(tmp_path: Path) -> None:
    input_root = tmp_path / "working" / "normalized" / "captures"
    output_root = tmp_path / "analysis"
    input_root.mkdir(parents=True)

    with pytest.raises(ValueError, match="assembled source datasets"):
        BalanceCheckWorkflow(
            facts=FilesystemFactRepository(),
            evidence=FilesystemEvidenceRepository(),
            artifacts=FilesystemArtifactStore(),
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
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    input_root.mkdir()
    for source_name in ("clean-source", "issue-source"):
        (input_root / source_name).mkdir()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)

    facts.write_facts(
        input_root / "clean-source" / "facts.csv",
        (
            _fact(
                fact_id="fact-clean",
                source="clean-source",
                timestamp=as_of,
                location_id="clean-source",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "clean-source" / "balance_references.csv",
        (
            _reference(
                source="clean-source",
                instrument_id="BTC",
                quantity="1.0",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )
    facts.write_facts(
        input_root / "issue-source" / "facts.csv",
        (
            _fact(
                fact_id="fact-issue",
                source="issue-source",
                timestamp=as_of,
                location_id="issue-source",
                instrument_id="ETH",
                quantity="2.0",
            ),
        ),
    )

    response = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.clean_source_count == 1
    assert response.issue_source_count == 1
    assert (output_root / "clean-source" / "balance_assertions.csv").exists()
    assert (output_root / "issue-source" / "reconciliation_issues.csv").exists()
    assert rows[0]["source"] == "clean-source"
    assert rows[1]["source"] == "issue-source"


def test_balance_check_workflow_uses_operator_assertions_when_selected(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    as_of = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
    input_root.mkdir()

    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.OPERATOR_ASSERTION,
            ),
        ),
    )

    response = BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert response.clean_source_count == 1
    assert response.resolution_mode == "offline"
    assert assertion_rows[0]["selected_reference_kind"] == "operator_assertion"
    assert check_summary_rows[0]["resolution_mode"] == "offline"
    assert check_summary_rows[0]["latest_clean_checked_date"] == "2025-12-31"
    assert (
        check_summary_rows[0]["selected_reference_kind_counts"]
        == '{"operator_assertion": 1}'
    )


def test_balance_check_workflow_respects_explicit_as_of_values(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    input_root.mkdir()

    earlier = datetime(2025, 12, 30, 0, 0, 0, tzinfo=UTC)
    later = datetime(2025, 12, 31, 0, 0, 0, tzinfo=UTC)
    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=earlier,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
            _fact(
                fact_id="fact-2",
                source="coinbase",
                timestamp=later,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="2.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=earlier,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
            as_of_values=("2025-12-30 00:00:00",),
            hydrate_missing_references=False,
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert len(assertion_rows) == 1
    assert check_summary_rows[0]["resolution_mode"] == "offline"
    assert assertion_rows[0]["target_at"] == "2025-12-30 00:00:00"
    assert assertion_rows[0]["snapshot_quantity"] == "1"
    assert assertion_rows[0]["status"] == "matched"


def test_balance_check_workflow_respects_explicit_date_only_as_of_values(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    input_root.mkdir()

    as_of = datetime(2025, 12, 30, tzinfo=UTC)
    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=as_of,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=as_of,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
            as_of_values=("2025-12-30",),
            hydrate_missing_references=False,
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")
    check_summary_rows = artifacts.read_rows(output_root / "balance_check_summary.csv")

    assert len(assertion_rows) == 1
    assert check_summary_rows[0]["resolution_mode"] == "offline"
    assert assertion_rows[0]["target_at"] == "2025-12-30 00:00:00"
    assert assertion_rows[0]["target_precision"] == "timestamp"
    assert check_summary_rows[0]["max_assertion_date"] == "2025-12-30"


def test_balance_check_workflow_matches_date_only_as_of_to_same_instant_reference(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    input_root.mkdir()

    fact_time = datetime(2025, 12, 30, tzinfo=UTC)
    reference_time = fact_time
    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=fact_time,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=reference_time,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
            as_of_values=("2025-12-30",),
            hydrate_missing_references=False,
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")

    assert len(assertion_rows) == 1
    assert assertion_rows[0]["status"] == "matched"
    assert assertion_rows[0]["selected_reference_kind"] == "source_document"
    assert assertion_rows[0]["observation_gap"] == "0"


def test_balance_check_workflow_applies_timezone_to_date_only_as_of_values(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "coinbase"
    output_root = tmp_path / "analysis"
    facts = FilesystemFactRepository()
    evidence = FilesystemEvidenceRepository()
    artifacts = FilesystemArtifactStore()
    input_root.mkdir()

    cutoff_at = datetime(2025, 12, 30, 7, 0, 0, tzinfo=UTC)
    facts.write_facts(
        input_root / "facts.csv",
        (
            _fact(
                fact_id="fact-1",
                source="coinbase",
                timestamp=cutoff_at,
                location_id="coinbase",
                instrument_id="BTC",
                quantity="1.0",
            ),
        ),
    )
    evidence.write_balance_references(
        input_root / "balance_references.csv",
        (
            _reference(
                source="coinbase",
                instrument_id="BTC",
                quantity="1.0",
                target_at=cutoff_at,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            ),
        ),
    )

    BalanceCheckWorkflow(
        facts=facts,
        evidence=evidence,
        artifacts=artifacts,
    ).execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(input_root),
            output_root_ref=to_resource_ref(output_root),
            as_of_values=("2025-12-30",),
            timezone="America/Denver",
            hydrate_missing_references=False,
        )
    )

    assertion_rows = artifacts.read_rows(output_root / "balance_assertions.csv")

    assert len(assertion_rows) == 1
    assert assertion_rows[0]["target_at"] == "2025-12-30 07:00:00"
    assert assertion_rows[0]["status"] == "matched"
