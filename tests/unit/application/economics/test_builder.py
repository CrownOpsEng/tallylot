from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.adapters.sources.platforms.coinbase.adapter import _CoinbaseAdapter
from tallylot.application.claim import build_coinbase_claim_set
from tallylot.application.economics import build_economic_facts
from tallylot.application.evidence.evidence_sets import build_evidence_set_for_profile
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.application.normalization.translation_inputs import (
    plan_translation_inputs,
)
from tallylot.application.profiling import BuildProfileUseCase
from tallylot.domain.claim import (
    ClaimBundleDecisionBasis,
    ClaimBundleDecisionOutcome,
    ClaimBundleDecisionRecord,
    ClaimBundleRecord,
    ClaimKind,
    ClaimLegSpec,
    ClaimRecord,
    ClaimRecordStatus,
    ClaimSet,
)
from tallylot.domain.economics import EconomicEventKind, EconomicLegRole, LifecycleEvent
from tallylot.domain.temporal import TemporalPrecision
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_profiles import SourceProfile


def _coinbase_profile(raw_dir: Path) -> SourceProfile:
    return BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile(
        "coinbase",
        raw_dir,
    )


def _retail_csv(*rows: str) -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,"
        "Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),"
        "Fees and/or Spread,Notes\n"
        f"{''.join(rows)}"
    )


def _build_claim_set(raw_dir: Path) -> ClaimSet:
    registry = build_registry()
    adapter = _CoinbaseAdapter()
    profile = _coinbase_profile(raw_dir)
    planning_result = plan_translation_inputs(
        profile=profile,
        candidates=adapter.describe_translation_inputs(profile, raw_dir),
    )
    statement_documents = StatementExtractionService(
        registry
    ).collect_source_statement_documents(profile, raw_dir)
    evidence_set = build_evidence_set_for_profile(
        profile=profile,
        capture_uid="capture-1",
        capture_manifest_fingerprint="manifest-1",
        planner_result=planning_result,
        statement_documents=statement_documents,
    )
    assert evidence_set is not None
    batch = adapter.translate_selected_inputs(profile, raw_dir, planning_result.plan)
    result = build_coinbase_claim_set(
        profile=profile,
        evidence_set=evidence_set,
        evidence_set_ref=(
            f"working/products/evidence_sets/{evidence_set.evidence_set_id}/evidence_set.json"
        ),
        planning_result=planning_result,
        batch=batch,
    )
    assert result is not None
    return result.claim_set


@pytest.mark.parametrize(
    ("row_text", "expected_kind", "expected_lifecycle", "expected_roles"),
    (
        (
            "tx-buy,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
            "Bought 0.01 BTC for 610 CAD\n",
            EconomicEventKind.ASSET_MOVEMENT,
            LifecycleEvent.CREATED,
            (
                EconomicLegRole.HOLDING_CHANGE,
                EconomicLegRole.CASH_CHANGE,
                EconomicLegRole.FEE,
            ),
        ),
        (
            "tx-sell,2024-02-08 16:31:22 UTC,Sell,BTC,0.01000000,CAD,$60000.00,$600.00,$590.00,$10.00,"
            "Sold 0.01 BTC for 590 CAD\n",
            EconomicEventKind.ASSET_MOVEMENT,
            LifecycleEvent.CREATED,
            (
                EconomicLegRole.CASH_CHANGE,
                EconomicLegRole.HOLDING_CHANGE,
                EconomicLegRole.FEE,
            ),
        ),
        (
            "tx-receive,2024-02-09 10:00:00 UTC,Receive,ETH,1.50000000,CAD,$0.00,$0.00,$0.00,$0.00,"
            "Received ETH\n",
            EconomicEventKind.ASSET_MOVEMENT,
            LifecycleEvent.CREATED,
            (EconomicLegRole.HOLDING_CHANGE,),
        ),
        (
            "tx-send,2024-02-08 17:31:22 UTC,Send,ETH,-0.50000000,CAD,$0.00,$0.00,$0.00,$0.00,"
            "Sent ETH\n",
            EconomicEventKind.ASSET_MOVEMENT,
            LifecycleEvent.CREATED,
            (EconomicLegRole.HOLDING_CHANGE,),
        ),
        (
            "reward-1,2023-03-18 01:28:49 UTC,Reward Income,ADA,0.000021,CAD,$0.48,$0.00,$0.00,$0.00,"
            "Received 0.000021 ADA from Coinbase Rewards\n",
            EconomicEventKind.FEE_OR_REBATE,
            LifecycleEvent.CREATED,
            (EconomicLegRole.REBATE,),
        ),
        (
            "migration-neg,2025-10-17 13:38:17 UTC,Asset Migration,MATIC,-1.65526374,CAD,$0.25,-$0.42,-$0.42,$0.00,\n"
            "migration-pos,2025-10-17 13:38:17 UTC,Asset Migration,POL,1.65526374,CAD,$0.25,$0.42,$0.42,$0.00,\n",
            EconomicEventKind.CORRECTION,
            LifecycleEvent.MIGRATED,
            (EconomicLegRole.HOLDING_CHANGE, EconomicLegRole.HOLDING_CHANGE),
        ),
    ),
)
def test_builder_maps_supported_coinbase_rows_to_declared_events_and_legs(
    tmp_path: Path,
    row_text: str,
    expected_kind: EconomicEventKind,
    expected_lifecycle: LifecycleEvent,
    expected_roles: tuple[EconomicLegRole, ...],
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(_retail_csv(row_text), encoding="utf-8")

    economic_facts = build_economic_facts(
        claim_set=_build_claim_set(raw_dir),
        claim_set_ref="working/products/claim_sets/claim-set-1/claim_set.json",
    )

    assert len(economic_facts.economic_event_records) == 1
    assert economic_facts.economic_event_records[0].kind is expected_kind
    assert (
        economic_facts.economic_event_records[0].lifecycle_event is expected_lifecycle
    )
    assert tuple(record.role for record in economic_facts.economic_leg_records) == (
        expected_roles
    )


def test_builder_skips_balance_only_claim_bundles() -> None:
    claim_set = _balance_only_claim_set()

    economic_facts = build_economic_facts(
        claim_set=claim_set,
        claim_set_ref="working/products/claim_sets/claim-set-1/claim_set.json",
    )

    assert economic_facts.economic_event_records == ()
    assert economic_facts.economic_leg_records == ()
    assert economic_facts.valuation_records == ()


def test_builder_fails_closed_for_unsupported_activity_shape() -> None:
    claim_set = _activity_claim_set(activity_label="deposit")

    with pytest.raises(
        ValueError, match="unsupported accepted activity shape: deposit"
    ):
        build_economic_facts(
            claim_set=claim_set,
            claim_set_ref="working/products/claim_sets/claim-set-1/claim_set.json",
        )


def _activity_claim_set(*, activity_label: str) -> ClaimSet:
    claim_set_id = "claim-set-1"
    scope_id = "scope-1"
    bundle_id = "bundle-1"
    activity_claim = ClaimRecord(
        claim_set_id=claim_set_id,
        scope_id=scope_id,
        bundle_id=bundle_id,
        claim_id="claim-activity",
        kind=ClaimKind.ACTIVITY,
        status=ClaimRecordStatus.ASSERTED,
        key=("row-1",),
        member_refs=("member-1",),
        observation_refs=(),
        effective_at=datetime(2024, 2, 8, 16, 31, 22, tzinfo=UTC),
        precision=TemporalPrecision.TIMESTAMP,
        provenance_refs=("file:row:1",),
        activity_label=activity_label,
        location_claim_ref="claim-location",
        leg_specs=(
            ClaimLegSpec(
                slot=0,
                role="asset_in",
                quantity=Decimal("1.25"),
                instrument_claim_refs=("claim-instrument",),
                location_claim_ref="claim-location",
                subtype="",
            ),
        ),
    )
    return ClaimSet(
        claim_set_id=claim_set_id,
        evidence_set_ref="working/products/evidence_sets/evidence-1/evidence_set.json",
        emitter_id="coinbase:claim",
        claim_records=(
            activity_claim,
            ClaimRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                bundle_id=bundle_id,
                claim_id="claim-owner",
                kind=ClaimKind.BENEFICIAL_OWNER,
                status=ClaimRecordStatus.ASSERTED,
                key=("owner",),
                member_refs=("member-1",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=("file:row:1",),
                beneficial_owner_ref="beneficial_owner:filing",
            ),
            ClaimRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                bundle_id=bundle_id,
                claim_id="claim-instrument",
                kind=ClaimKind.INSTRUMENT,
                status=ClaimRecordStatus.ASSERTED,
                key=("instrument",),
                member_refs=("member-1",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=("file:row:1",),
                scheme="asset",
                value="BTC",
                venue="",
                instrument_kind="crypto",
                name="Bitcoin",
            ),
            ClaimRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                bundle_id=bundle_id,
                claim_id="claim-location",
                kind=ClaimKind.LOCATION,
                status=ClaimRecordStatus.ASSERTED,
                key=("location",),
                member_refs=("member-1",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=("file:row:1",),
                location_ref="location:coinbase",
                location_group_label="Coinbase",
                location_label="Coinbase",
            ),
        ),
        claim_bundle_records=(
            ClaimBundleRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                bundle_id=bundle_id,
                key="row-1",
                scope_key=("member-1", "row-1"),
                claim_refs=(
                    "claim-activity",
                    "claim-owner",
                    "claim-instrument",
                    "claim-location",
                ),
            ),
        ),
        claim_bundle_decision_records=(
            ClaimBundleDecisionRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                decision_id="decision-1",
                outcome=ClaimBundleDecisionOutcome.ACCEPTED,
                accepted_bundle_ref=bundle_id,
                rejected_bundle_refs=(),
                deferred_bundle_refs=(),
                basis=ClaimBundleDecisionBasis.SINGLE_BUNDLE,
                blocking_gap_refs=(),
            ),
        ),
    )


def _balance_only_claim_set() -> ClaimSet:
    claim_set_id = "claim-set-1"
    scope_id = "scope-balance"
    bundle_id = "bundle-balance"
    return ClaimSet(
        claim_set_id=claim_set_id,
        evidence_set_ref="working/products/evidence_sets/evidence-1/evidence_set.json",
        emitter_id="coinbase:claim",
        claim_records=(
            ClaimRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                bundle_id=bundle_id,
                claim_id="claim-balance",
                kind=ClaimKind.BALANCE,
                status=ClaimRecordStatus.ASSERTED,
                key=("balance",),
                member_refs=("member-1",),
                observation_refs=("observation-1",),
                effective_at=None,
                precision=TemporalPrecision.TIMESTAMP,
                provenance_refs=("statement:row:1",),
                location_claim_ref="claim-location",
                instrument_claim_refs=("claim-instrument",),
                balance_kind="asset_balance",
                quantity=Decimal("1.25"),
                observed_at=datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC),
            ),
            ClaimRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                bundle_id=bundle_id,
                claim_id="claim-instrument",
                kind=ClaimKind.INSTRUMENT,
                status=ClaimRecordStatus.ASSERTED,
                key=("instrument",),
                member_refs=("member-1",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=("statement:row:1",),
                scheme="asset",
                value="ETH",
                venue="",
                instrument_kind="crypto",
                name="Ethereum",
            ),
            ClaimRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                bundle_id=bundle_id,
                claim_id="claim-location",
                kind=ClaimKind.LOCATION,
                status=ClaimRecordStatus.ASSERTED,
                key=("location",),
                member_refs=("member-1",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=("statement:row:1",),
                location_ref="location:coinbase",
                location_group_label="Coinbase",
                location_label="Coinbase",
            ),
        ),
        claim_bundle_records=(
            ClaimBundleRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                bundle_id=bundle_id,
                key="statement-row-1",
                scope_key=("member-1", "statement-row-1"),
                claim_refs=("claim-balance", "claim-instrument", "claim-location"),
            ),
        ),
        claim_bundle_decision_records=(
            ClaimBundleDecisionRecord(
                claim_set_id=claim_set_id,
                scope_id=scope_id,
                decision_id="decision-balance",
                outcome=ClaimBundleDecisionOutcome.ACCEPTED,
                accepted_bundle_ref=bundle_id,
                rejected_bundle_refs=(),
                deferred_bundle_refs=(),
                basis=ClaimBundleDecisionBasis.SINGLE_BUNDLE,
                blocking_gap_refs=(),
            ),
        ),
    )
