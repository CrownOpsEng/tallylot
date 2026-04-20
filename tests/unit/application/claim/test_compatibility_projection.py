from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.coinbase.adapter import _CoinbaseAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.application.claim import build_coinbase_claim_set
from tallylot.application.compatibility import project_translation_batch_from_claim_set
from tallylot.application.evidence.evidence_sets import build_evidence_set_for_profile
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.application.normalization.translation_inputs import (
    plan_translation_inputs,
)
from tallylot.application.profiling import BuildProfileUseCase
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_profiles import SourceProfile
from tallylot.domain.transactions import TransactionFact


def _coinbase_profile(raw_dir: Path) -> SourceProfile:
    return BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile(
        "coinbase",
        raw_dir,
    )


def _projected_facts(
    raw_dir: Path,
) -> tuple[tuple[TransactionFact, ...], tuple[TransactionFact, ...]]:
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
        evidence_set_ref=f"working/products/evidence_sets/{evidence_set.evidence_set_id}/evidence_set.json",
        planning_result=planning_result,
        batch=selected_batch,
    )
    assert claim_build is not None
    projected = project_translation_batch_from_claim_set(
        claim_set=claim_build.claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=claim_build.draft_projection_field_records,
        gap_records=claim_build.gap_records,
        gap_explanations=claim_build.gap_explanations,
        review_records=claim_build.review_records,
        review_explanations=claim_build.review_explanations,
    )
    return compile_activity_drafts(selected_batch.drafts), compile_activity_drafts(
        projected.drafts
    )


def test_claim_projection_preserves_supported_coinbase_bridge_values(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        "Transactions\nUser,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-buy,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,Bought 0.01 BTC\n"
        "tx-sell,2024-02-08 16:31:22 UTC,Sell,BTC,0.01000000,CAD,$60000.00,$600.00,$590.00,$10.00,Sold 0.01 BTC\n"
        "reward-1,2023-03-18 01:28:49 UTC,Reward Income,ADA,0.000021,CAD,$0.48,$0.00,$0.00,$0.00,Received ADA\n"
        "tx-receive,2024-02-09 10:00:00 UTC,Receive,ETH,1.50000000,CAD,$0.00,$0.00,$0.00,$0.00,Received ETH\n"
        "tx-send,2024-02-08 17:31:22 UTC,Send,ETH,-0.50000000,CAD,$0.00,$0.00,$0.00,$0.00,Sent ETH\n"
        "migration-neg,2025-10-17 13:38:17 UTC,Asset Migration,MATIC,-1.65526374,CAD,$0.25,-$0.42,-$0.42,$0.00,\n"
        "migration-pos,2025-10-17 13:38:17 UTC,Asset Migration,POL,1.65526374,CAD,$0.25,$0.42,$0.42,$0.00,\n",
        encoding="utf-8",
    )

    expected, projected = _projected_facts(raw_dir)

    for projected_fact, expected_fact in zip(projected, expected, strict=True):
        projected_row = projected_fact.to_row()
        expected_row = expected_fact.to_row()
        for key in (
            "fact_id",
            "timestamp",
            "location_id",
            "economic_kind",
            "projection_hint",
            "accounting_intent_hint",
            "tax_treatment_hint",
            "description",
            "provider_operation_key",
            "tx_hash",
            "raw_file",
            "raw_row_ref",
            "legs",
        ):
            assert projected_row[key] == expected_row[key]
