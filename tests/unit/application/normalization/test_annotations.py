from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.application.normalization.annotations import (
    annotation_records_from_drafts,
)
from tallylot.adapters.sources.platforms.coinbase.adapter import _CoinbaseAdapter
from tallylot.application.claim import build_coinbase_claim_set
from tallylot.application.claim.contracts import CoinbaseClaimBuildResult
from tallylot.application.compatibility.economic_facts import (
    project_compatibility_artifacts_from_economic_facts,
)
from tallylot.application.economics import build_economic_facts
from tallylot.application.evidence.evidence_sets import build_evidence_set_for_profile
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.application.normalization.translation_inputs import (
    plan_translation_inputs,
)
from tallylot.application.profiling import BuildProfileUseCase
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    AccountingIntentHint,
    EconomicKind,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId
from tallylot.domain.evidence import EvidenceSet
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import (
    EconomicActivityDraft,
    SourceTranslationBatch,
    classification,
    economic_leg,
)


def test_annotation_records_preserve_draft_provenance_and_review_markers() -> None:
    records = annotation_records_from_drafts(
        (
            EconomicActivityDraft(
                activity_id="txn-1",
                source="fixture",
                adapter_id="fixture",
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                location_id=LocationId("fixture:primary"),
                classification=classification(
                    economic_kind=EconomicKind.SPOT_TRADE,
                    projection_hint=ProjectionHint.TRADE,
                    accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                    tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                ),
                legs=(
                    economic_leg(
                        leg_id="primary_btc",
                        kind=LegKind.PRIMARY,
                        instrument="BTC",
                        quantity=Decimal("1"),
                    ),
                ),
                leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                provenance_refs=("file:row:2", "statement:page:1"),
                review_markers=("normalized_negative_fee",),
            ),
        )
    )

    assert [record.to_json() for record in records] == [
        {
            "fact_id": "txn-1",
            "provenance_refs": ["file:row:2", "statement:page:1"],
            "review_markers": ["normalized_negative_fee"],
            "adapter_metadata": [],
        }
    ]


def _coinbase_profile(raw_dir: Path) -> SourceProfile:
    return BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile(
        "coinbase",
        raw_dir,
    )


def _claim_build(
    raw_dir: Path,
) -> tuple[SourceTranslationBatch, CoinbaseClaimBuildResult, EvidenceSet]:
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
    selected_batch = adapter.translate_selected_inputs(
        profile, raw_dir, planning_result.plan
    )
    claim_build = build_coinbase_claim_set(
        profile=profile,
        evidence_set=evidence_set,
        planning_result=planning_result,
        batch=selected_batch,
    )
    assert claim_build is not None
    return selected_batch, claim_build, evidence_set


def test_economic_facts_projection_preserves_fact_annotation_payloads(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        "Transactions\nUser,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-buy,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,Bought 0.01 BTC\n"
        "tx-receive,2024-02-09 10:00:00 UTC,Receive,ETH,1.50000000,CAD,$0.00,$0.00,$0.00,$0.00,Received ETH\n",
        encoding="utf-8",
    )

    selected_batch, claim_build, evidence_set = _claim_build(raw_dir)
    expected = [
        record.to_json()
        for record in annotation_records_from_drafts(selected_batch.drafts)
    ]
    economic_facts = build_economic_facts(claim_set=claim_build.claim_set)
    projected = project_compatibility_artifacts_from_economic_facts(
        economic_facts=economic_facts,
        claim_set=claim_build.claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=claim_build.draft_projection_field_records,
    )

    assert [record.to_json() for record in projected.fact_annotations] == expected
