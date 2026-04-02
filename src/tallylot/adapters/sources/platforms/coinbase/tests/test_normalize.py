from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.coinbase.adapter import CoinbaseAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.transactions import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
from tests.support.services import build_source_profile


def test_coinbase_adapter_reports_missing_retail_csv_as_explicit_issue(tmp_path: Path) -> None:
    result = CoinbaseAdapter().translate(
        build_source_profile(adapter_id="coinbase", raw_dir=str(tmp_path)),
        tmp_path,
    )

    assert not compile_activity_drafts(result.drafts)
    assert result.issues[0].kind == "missing_required_input"
    assert "retail all-time CSV" in result.issues[0].message


def test_coinbase_adapter_normalizes_buy_row_from_header_detected_csv(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Bought 0.01 BTC for 610 CAD\n",
        encoding="utf-8",
    )

    result = CoinbaseAdapter().translate(
        build_source_profile(adapter_id="coinbase", raw_dir=str(raw_dir)),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    event = facts[0]

    assert len(facts) == 1
    assert event.economic_kind == EconomicKind.SPOT_TRADE
    assert event.projection_type == ProjectionType.TRADE
    assert event.journal_intent == JournalIntent.ASSET_EXCHANGE
    assert event.tax_treatment_code == TaxTreatmentCode.CAPITAL_EXCHANGE
    assert str(event.legs[0].asset) == "BTC"
    assert str(event.legs[1].asset) == "CAD"
    assert str(event.legs[0].amount) == "0.01"
    assert event.legs[1].amount == 600


def test_coinbase_adapter_normalizes_sell_send_and_receive_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-sell,2024-02-08 16:31:22 UTC,Sell,BTC,0.01000000,CAD,$60000.00,$600.00,$590.00,$10.00,"
        "Sold 0.01 BTC for 590 CAD\n"
        "tx-send,2024-02-08 17:31:22 UTC,Send,ETH,-0.50000000,CAD,$0.00,$0.00,$0.00,$0.00,"
        "Sent ETH\n"
        "tx-receive,2024-02-09 10:00:00 UTC,Receive,ETH,1.50000000,CAD,$0.00,$0.00,$0.00,$0.00,"
        "Received ETH\n",
        encoding="utf-8",
    )

    result = CoinbaseAdapter().translate(
        build_source_profile(adapter_id="coinbase", raw_dir=str(raw_dir)),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    sell_event, send_event, receive_event = facts

    assert len(facts) == 3
    assert sell_event.economic_kind == EconomicKind.SPOT_TRADE
    assert sell_event.projection_type == ProjectionType.TRADE
    assert str(sell_event.legs[0].asset) == "CAD"
    assert str(sell_event.legs[1].asset) == "BTC"
    assert send_event.economic_kind == EconomicKind.ASSET_WITHDRAWAL
    assert send_event.projection_type == ProjectionType.WITHDRAWAL
    assert str(send_event.legs[0].asset) == "ETH"
    assert receive_event.economic_kind == EconomicKind.ASSET_DEPOSIT
    assert receive_event.projection_type == ProjectionType.DEPOSIT
    assert str(receive_event.legs[0].asset) == "ETH"
    assert not result.issues


def test_coinbase_adapter_surfaces_unsupported_rows_without_dropping_supported_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "tx-1,2024-02-08 16:31:22 UTC,Buy,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Bought 0.01 BTC for 610 CAD\n"
        "tx-2,2024-02-10 12:00:00 UTC,Convert,BTC,0.01000000,CAD,$60000.00,$600.00,$610.00,$10.00,"
        "Unsupported convert row\n",
        encoding="utf-8",
    )

    result = CoinbaseAdapter().translate(
        build_source_profile(adapter_id="coinbase", raw_dir=str(raw_dir)),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 1
    assert facts[0].projection_type == ProjectionType.TRADE
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_row"


def test_coinbase_adapter_normalizes_reward_income_and_asset_migration_pair(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "retail-export.csv").write_text(
        "Transactions\n"
        "User,Example User,acct\n"
        "ID,Timestamp,Transaction Type,Asset,Quantity Transacted,Price Currency,Price at Transaction,"
        "Subtotal,Total (inclusive of fees and/or spread),Fees and/or Spread,Notes\n"
        "reward-1,2023-03-18 01:28:49 UTC,Reward Income,ADA,0.000021,CAD,$0.48,$0.00,$0.00,$0.00,"
        "Received 0.000021 ADA from Coinbase Rewards\n"
        "migration-neg,2025-10-17 13:38:17 UTC,Asset Migration,MATIC,-1.65526374,CAD,$0.25,-$0.42,-$0.42,$0.00,\n"
        "migration-pos,2025-10-17 13:38:17 UTC,Asset Migration,POL,1.65526374,CAD,$0.25,$0.42,$0.42,$0.00,\n",
        encoding="utf-8",
    )

    result = CoinbaseAdapter().translate(
        build_source_profile(adapter_id="coinbase", raw_dir=str(raw_dir)),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    reward_event, migration_event = facts

    assert len(facts) == 2
    assert reward_event.economic_kind == EconomicKind.INTEREST_INCOME
    assert reward_event.projection_type == ProjectionType.INTEREST_INCOME
    assert str(reward_event.legs[0].asset) == "ADA"
    assert migration_event.economic_kind == EconomicKind.ASSET_MIGRATION
    assert migration_event.projection_type == ProjectionType.SWAP_NON_TAXABLE
    assert migration_event.description == "Coinbase Asset Migration"
    assert str(migration_event.legs[0].asset) == "POL"
    assert str(migration_event.legs[1].asset) == "MATIC"
    assert not result.issues
