from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tallylot.adapters.sources.platforms.coinbase.adapter import _CoinbaseAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.application.normalization.translation_inputs import (
    plan_translation_inputs,
)
from tallylot.application.profiling import BuildProfileUseCase
from tallylot.domain.transactions import EconomicKind
from tallylot.infrastructure.discovery import build_registry
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_profiles import SourceProfile


def test_coinbase_planner_selects_newer_broader_all_time_export(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    older_path = raw_dir / "2021 Statement.csv"
    newer_path = raw_dir / "2026-03-23 Statement - All Time.csv"
    older_path.write_text(older_retail_csv(), encoding="utf-8")
    newer_path.write_text(newer_all_time_retail_csv(), encoding="utf-8")
    adapter = _CoinbaseAdapter()
    profile = coinbase_profile(raw_dir)

    result = plan_translation_inputs(
        profile=profile,
        candidates=adapter.describe_translation_inputs(profile, raw_dir),
    )
    decisions = {decision.candidate_id: decision for decision in result.plan.decisions}

    assert result.plan.blocked is False
    assert result.plan.selected_candidate_ids == (
        f"coinbase:retail_export:{newer_path.name}",
    )
    assert decisions[f"coinbase:retail_export:{older_path.name}"].status == (
        "superseded_replaced"
    )
    assert decisions[
        f"coinbase:retail_export:{newer_path.name}"
    ].replaces_candidate_ids == (f"coinbase:retail_export:{older_path.name}",)


def test_coinbase_selected_plan_preserves_asset_migration_rows_without_aliasing(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "2021 Statement.csv").write_text(older_retail_csv(), encoding="utf-8")
    newer_path = raw_dir / "2026-03-23 Statement - All Time.csv"
    newer_path.write_text(newer_all_time_retail_csv(), encoding="utf-8")
    adapter = _CoinbaseAdapter()
    profile = coinbase_profile(raw_dir)
    planning_result = plan_translation_inputs(
        profile=profile,
        candidates=adapter.describe_translation_inputs(profile, raw_dir),
    )

    batch = adapter.translate_selected_inputs(profile, raw_dir, planning_result.plan)
    facts = compile_activity_drafts(batch.drafts)
    migration_event = next(
        fact for fact in facts if fact.economic_kind is EconomicKind.ASSET_MIGRATION
    )

    assert migration_event.timestamp == datetime(
        2025,
        10,
        17,
        13,
        38,
        17,
        tzinfo=UTC,
    )
    assert {str(leg.instrument_id) for leg in migration_event.legs} == {
        "symbol:MATIC@coinbase",
        "symbol:POL@coinbase",
    }


def test_coinbase_planner_blocks_ambiguous_overlapping_retail_exports(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "2021 statement a.csv").write_text(
        retail_csv_with_amount("tx-a", "1.00000000"),
        encoding="utf-8",
    )
    (raw_dir / "2021 statement b.csv").write_text(
        retail_csv_with_amount("tx-b", "2.00000000"),
        encoding="utf-8",
    )
    adapter = _CoinbaseAdapter()
    profile = coinbase_profile(raw_dir)

    result = plan_translation_inputs(
        profile=profile,
        candidates=adapter.describe_translation_inputs(profile, raw_dir),
    )

    assert result.plan.blocked is True
    assert {decision.status for decision in result.plan.decisions} == {
        "blocked_ambiguous_freshness"
    }


def coinbase_profile(raw_dir: Path) -> SourceProfile:
    return BuildProfileUseCase(
        build_registry(), FilesystemArtifactStore()
    ).create_profile(
        "coinbase",
        raw_dir,
    )


def older_retail_csv() -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "legacy-1,2021-12-30 08:56:53 UTC,Receive,FET,1.9859001,CAD,$0.64,$1.27098,$1.27098,$0.00,"
        "Received 1.9859001 FET\n"
    )


def newer_all_time_retail_csv() -> str:
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


def retail_csv_with_amount(transaction_id: str, amount: str) -> str:
    return (
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        f"{transaction_id},2021-12-30 08:56:53 UTC,Receive,FET,{amount},CAD,$0.64,$1.27098,$1.27098,$0.00,"
        "Received FET\n"
    )
