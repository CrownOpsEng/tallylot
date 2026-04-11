from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from tallylot.adapters.support import location_id_from_parts
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
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
from tallylot.domain.types import AdapterId, SourceId, TransactionId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import (
    FilesystemEvidenceRepository,
    FilesystemFactRepository,
)
from tests.support.skill_scripts import load_skill_main

if TYPE_CHECKING:
    import pytest


def _fact(
    source: str, instrument_id: str, quantity: str, as_of: datetime
) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId(f"{source}:{instrument_id}"),
        source=SourceId(source),
        adapter_id=AdapterId("structured_csv"),
        timestamp=as_of,
        location_id=location_id_from_parts(source),
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


def _reference(
    source: str, instrument_id: str, quantity: str, as_of: datetime
) -> BalanceReference:
    return BalanceReference(
        target=BalanceTarget(
            source=SourceId(source),
            location_id=location_id_from_parts(source),
            instrument_id=InstrumentId(instrument_id),
            balance_kind="available",
            target_at=as_of,
            target_precision=TemporalPrecision.TIMESTAMP,
        ),
        quantity=Decimal(quantity),
        reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
        observed_at=as_of,
        observed_precision=TemporalPrecision.TIMESTAMP,
        support_ref=f"{source}.csv",
    )


def _snapshot(
    source: str, instrument_id: str, quantity: str, as_of: datetime
) -> BalanceSnapshot:
    return BalanceSnapshot(
        target=BalanceTarget(
            source=SourceId(source),
            location_id=location_id_from_parts(source),
            instrument_id=InstrumentId(instrument_id),
            balance_kind="available",
            target_at=as_of,
            target_precision=TemporalPrecision.TIMESTAMP,
        ),
        quantity=Decimal(quantity),
        snapshot_basis="fact_cutoff",
    )


def test_reconciliation_balance_skill_runner_executes_runtime_workflows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_root = tmp_path / "normalized"
    analysis_root = tmp_path / "analysis"
    input_root.mkdir()
    (input_root / "clean-source").mkdir()
    (input_root / "issue-source").mkdir()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    evidence = FilesystemEvidenceRepository()
    facts = FilesystemFactRepository()

    facts.write_facts(
        input_root / "clean-source" / "facts.csv",
        (_fact("clean-source", "BTC", "1.0", as_of),),
    )
    evidence.write_balance_snapshots(
        input_root / "clean-source" / "balance_snapshots.csv",
        (_snapshot("clean-source", "BTC", "1.0", as_of),),
    )
    evidence.write_balance_references(
        input_root / "clean-source" / "balance_references.csv",
        (_reference("clean-source", "BTC", "1.0", as_of),),
    )
    facts.write_facts(
        input_root / "issue-source" / "facts.csv",
        (_fact("issue-source", "ETH", "2.0", as_of),),
    )
    evidence.write_balance_snapshots(
        input_root / "issue-source" / "balance_snapshots.csv",
        (_snapshot("issue-source", "ETH", "2.0", as_of),),
    )

    monkeypatch.chdir(tmp_path)
    main = load_skill_main(
        ".agents/skills/reconciliation-balance-operations/scripts/reconciliation_balance_operations.py"
    )

    exit_code = main(
        (
            "run",
            "--input-root",
            str(input_root),
            "--analysis-root",
            str(analysis_root),
        )
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    summary = json.loads(
        (analysis_root / "balance_reconciliation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    blocker_rows = FilesystemArtifactStore().read_rows(
        analysis_root / "balance_reconciliation_blockers.csv"
    )

    assert payload["summary_output_ref"] == str(
        analysis_root / "balance_reconciliation_summary.json"
    )
    assert summary["latest_portfolio_clean_date"] == ""
    assert summary["latest_portfolio_resolved_reference_date"] == ""
    assert summary["latest_clean_source_date"] == "2026-03-23"
    assert summary["latest_resolved_reference_date"] == "2026-03-23"
    assert summary["latest_observed_assertion_date"] == "2026-03-23"
    assert blocker_rows[0]["source"] == "issue-source"
