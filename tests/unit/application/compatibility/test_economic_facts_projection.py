from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tallylot.adapters.sources.platforms.coinbase.adapter import _CoinbaseAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
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
from tallylot.domain.evidence import EvidenceSet
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch


def _coinbase_profile(raw_dir: Path, *, source: str = "coinbase") -> SourceProfile:
    return BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile(
        source,
        raw_dir,
    )


def _claim_build(
    raw_dir: Path,
    *,
    source: str = "coinbase",
) -> tuple[SourceTranslationBatch, CoinbaseClaimBuildResult, EvidenceSet]:
    registry = build_registry()
    adapter = _CoinbaseAdapter()
    profile = _coinbase_profile(raw_dir, source=source)
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


def test_projection_preserves_supported_coinbase_bridge_rows(tmp_path: Path) -> None:
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

    selected_batch, claim_build, evidence_set = _claim_build(raw_dir)
    expected = compile_activity_drafts(selected_batch.drafts)
    economic_facts = build_economic_facts(claim_set=claim_build.claim_set)
    projected = project_compatibility_artifacts_from_economic_facts(
        economic_facts=economic_facts,
        claim_set=claim_build.claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=claim_build.draft_projection_field_records,
    )

    for projected_fact, expected_fact in zip(projected.facts, expected, strict=True):
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
            "operation_group_id",
            "tx_hash",
            "raw_file",
            "raw_row_ref",
            "legs",
            "leg_policy",
        ):
            assert projected_row[key] == expected_row[key]


def test_projection_requires_matching_claim_set_lineage(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        "Transactions\nUser,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-buy,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,Bought 0.01 BTC\n",
        encoding="utf-8",
    )

    _selected_batch, claim_build, evidence_set = _claim_build(raw_dir)
    economic_facts = replace(
        build_economic_facts(claim_set=claim_build.claim_set),
        claim_set_refs=("other-claim-set",),
    )

    with pytest.raises(
        ValueError,
        match="economic facts compatibility requires matching claim_set lineage",
    ):
        project_compatibility_artifacts_from_economic_facts(
            economic_facts=economic_facts,
            claim_set=claim_build.claim_set,
            evidence_set=evidence_set,
            draft_projection_field_records=claim_build.draft_projection_field_records,
        )


def test_projection_requires_projection_fields_for_each_claim_bundle(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        "Transactions\nUser,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-buy,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,Bought 0.01 BTC\n",
        encoding="utf-8",
    )

    _selected_batch, claim_build, evidence_set = _claim_build(raw_dir)
    economic_facts = build_economic_facts(claim_set=claim_build.claim_set)

    with pytest.raises(
        ValueError,
        match="economic facts compatibility requires draft projection fields",
    ):
        project_compatibility_artifacts_from_economic_facts(
            economic_facts=economic_facts,
            claim_set=claim_build.claim_set,
            evidence_set=evidence_set,
            draft_projection_field_records=(),
        )


def test_projection_replay_with_unchanged_inputs_preserves_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        "Transactions\nUser,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-buy,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,Bought 0.01 BTC\n",
        encoding="utf-8",
    )
    _selected_batch, claim_build, evidence_set = _claim_build(raw_dir)
    economic_facts = build_economic_facts(claim_set=claim_build.claim_set)

    first = project_compatibility_artifacts_from_economic_facts(
        economic_facts=economic_facts,
        claim_set=claim_build.claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=claim_build.draft_projection_field_records,
    )
    second = project_compatibility_artifacts_from_economic_facts(
        economic_facts=economic_facts,
        claim_set=claim_build.claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=claim_build.draft_projection_field_records,
    )

    assert tuple(fact.to_row() for fact in first.facts) == tuple(
        fact.to_row() for fact in second.facts
    )
    assert tuple(record.to_json() for record in first.fact_annotations) == tuple(
        record.to_json() for record in second.fact_annotations
    )


def test_projection_order_only_changes_do_not_change_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail.csv").write_text(
        "Transactions\nUser,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-buy,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,Bought 0.01 BTC\n",
        encoding="utf-8",
    )
    _selected_batch, claim_build, evidence_set = _claim_build(raw_dir)
    economic_facts = build_economic_facts(claim_set=claim_build.claim_set)
    reordered_economic_facts = replace(
        economic_facts,
        economic_event_records=tuple(reversed(economic_facts.economic_event_records)),
        economic_leg_records=tuple(reversed(economic_facts.economic_leg_records)),
    )

    first = project_compatibility_artifacts_from_economic_facts(
        economic_facts=economic_facts,
        claim_set=claim_build.claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=claim_build.draft_projection_field_records,
    )
    second = project_compatibility_artifacts_from_economic_facts(
        economic_facts=reordered_economic_facts,
        claim_set=claim_build.claim_set,
        evidence_set=evidence_set,
        draft_projection_field_records=claim_build.draft_projection_field_records,
    )

    assert tuple(fact.to_row() for fact in first.facts) == tuple(
        fact.to_row() for fact in second.facts
    )
