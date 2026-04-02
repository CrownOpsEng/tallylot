from __future__ import annotations

import json
from pathlib import Path

import pytest

import normalize_source
import pipeline_common
import source_adapters


def build_profile(source: str, raw_dir: Path) -> tuple[source_adapters.SourceAdapter, pipeline_common.SourceProfile]:
    initial_adapter = source_adapters.get_adapter(source)
    profile = pipeline_common.build_source_profile(
        source=source,
        raw_dir=raw_dir,
        adapter_name=initial_adapter.name,
        adapter_supported=initial_adapter.supported,
    )
    return source_adapters.get_adapter(source, profile), profile


@pytest.mark.parametrize(
    ("source", "expected_adapter", "supported"),
    [
        ("Coinbase", "coinbase", True),
        ("WealthSimple", "wealthsimple", True),
        ("Binance", "binance", True),
        ("Crypto.com", "crypto_com", True),
        ("Shakepay", "shakepay", True),
        ("ledger-live-main", "ledger_live", True),
        ("near-main", "near", True),
        ("GTrade 1CT", "gtrade", True),
        ("bsc-metamask1", "evm_explorer", True),
        ("Ledger Live", "ledger_live", True),
        ("NEAR Wallet", "near", True),
    ],
)
def test_get_adapter_resolves_supported_sources(source: str, expected_adapter: str, supported: bool) -> None:
    adapter = source_adapters.get_adapter(source)

    assert adapter.name == expected_adapter
    assert adapter.supported is supported


def test_get_adapter_can_resolve_from_profile_before_source_label(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "broker-export.csv").write_text(
        "transaction_date,settlement_date,account_id,account_type,activity_type,activity_sub_type\n"
        "2023-09-21,,acct,Crypto,Trade,BUY\n",
        encoding="utf-8",
    )

    profile = pipeline_common.build_source_profile(
        source="Future Broker",
        raw_dir=raw_dir,
        adapter_name="generic",
        adapter_supported=False,
    )

    assert source_adapters.get_adapter("Future Broker", profile).name == "wealthsimple"


def test_load_exception_decisions_filters_by_manifest_fingerprint(tmp_path: Path) -> None:
    path = tmp_path / "exception_decisions.csv"
    path.write_text(
        (
            "manifest_fingerprint,event_id,resolution_status,resolution_note\n"
            "abc,evt-1,accepted,handled once\n"
            "other,evt-2,accepted,ignore\n"
        ),
        encoding="utf-8",
    )

    decisions = source_adapters.load_exception_decisions(path, "abc")

    assert decisions["evt-1"] == {"resolution_status": "accepted", "resolution_note": "handled once"}
    assert "evt-2" not in decisions


def test_shakepay_adapter_normalizes_minimal_fixture(tmp_path: Path) -> None:
    raw_dir = tmp_path / "shakepay" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "cash_transactions_summary.csv").write_text(
        "Date,Type,Description,Debit,Credit,Spot Rate,Buy / Sell Rate,Balance\n"
        "2024-01-01 09:10:11,Interac e-Transfer,CAD deposit,,100.00,,,100.00\n",
        encoding="utf-8",
    )
    (raw_dir / "crypto_transactions_summary.csv").write_text(
        "Date,Amount Debited,Asset Debited,Amount Credited,Asset Credited,Market Value,Market Value Currency,Book Cost,Book Cost Currency,Type,Spot Rate,Buy / Sell Rate,Description\n"
        "2024-01-02 09:10:11,,,0.00010000,BTC,6.00,CAD,0.00,CAD,Reward,,,ShakingSats\n",
        encoding="utf-8",
    )
    adapter, profile = build_profile("Shakepay", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert adapter.name == "shakepay"
    assert {row["event_kind"] for row in result.canonical_events} == {"Deposit", "Reward / Bonus"}
    assert any(row["description"] == "shakingsats" for row in result.canonical_events)
    assert result.canonical_balances == []
    assert result.exceptions == []


def test_ledger_live_adapter_normalizes_grouped_trade_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "ledger" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "ledgerlive-operations.csv").write_text(
        (
            "Operation Date,Status,Currency Ticker,Operation Type,Operation Amount,Operation Fees,Account Name,Account xpub,Operation Hash\n"
            "2026-03-23T10:11:12.000Z,Confirmed,BTC,IN,0.01000000,,Bitcoin 1,xpub6A111111111111111111111111111111111111111111111111111111111111111111111111111111111111111,op-1\n"
            "2026-03-23T10:11:12.000Z,Confirmed,ETH,OUT,0.50000000,,Bitcoin 1,xpub6A111111111111111111111111111111111111111111111111111111111111111111111111111111111111111,op-1\n"
            "2026-03-23T10:11:12.000Z,Confirmed,ETH,FEES,0.01000000,,Bitcoin 1,xpub6A111111111111111111111111111111111111111111111111111111111111111111111111111111111111111,op-1\n"
        ),
        encoding="utf-8",
    )
    adapter, profile = build_profile("ledger-live-main", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert adapter.name == "ledger_live"
    assert len(result.canonical_events) == 1
    assert result.canonical_events[0]["event_kind"] == "Trade"
    assert result.canonical_events[0]["amount_in"] == "0.01000000"
    assert result.canonical_events[0]["asset_out"] == "ETH"
    assert result.canonical_events[0]["fee_amount"] == "0.01000000"
    assert result.exceptions == []


def test_near_adapter_normalizes_transfer_and_stake_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path / "near" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "example.near_transactions.csv").write_text(
        (
            "Txn Hash,Time,Status,Method,Deposit Value,Txn Fee,To\n"
            "tx-1,2024-01-01 00:00:00,Success,TRANSFER,1.00000000,0.01000000,example.near\n"
            "tx-2,2024-01-02 00:00:00,Success,deposit_and_stake,2.00000000,0.10000000,example.near\n"
        ),
        encoding="utf-8",
    )
    adapter, profile = build_profile("capture-near", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert adapter.name == "near"
    assert [row["event_kind"] for row in result.canonical_events] == ["Deposit", "Withdrawal", "Deposit"]
    assert any(row["source"].endswith("Staking") for row in result.canonical_events)
    assert result.exceptions == []


def test_gtrade_adapter_surfaces_report_limits_without_guessing(tmp_path: Path) -> None:
    raw_dir = tmp_path / "gtrade" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "gtrade-report.csv").write_text(
        (
            "DATE,PAIR,ADDR,TYPE,DIR,DESCRIPTION,PNL\n"
            "06/05/2023,BTC-USD,bb4d,close,long,Closed profit,10\n"
            "07/05/2023,BTC-USD,bb4d,close,short,Closed loss,-5\n"
            "08/05/2023,BTC-USD,bb4d,close,flat,No pnl,0\n"
        ),
        encoding="utf-8",
    )
    adapter, profile = build_profile("GTrade 1CT", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert adapter.name == "gtrade"
    assert [row["event_kind"] for row in result.canonical_events] == [
        "Derivatives / Futures Profit",
        "Derivatives / Futures Loss",
    ]
    assert len(result.exceptions) == 1
    assert result.exceptions[0]["exception_kind"] == "unsupported_row"


def test_binance_adapter_handles_supported_and_review_required_rows(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv").write_text(
        (
            "Time,Pair,Side,Price,Executed,Amount,Fee\n"
            "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n"
        ),
        encoding="utf-8",
    )
    (raw_dir / "Binance-Deposit-History-202603230411(UTC--6)_abcd.csv").write_text(
        (
            "Time,Coin,Network,Amount,Address,TXID,Status\n"
            "23-05-06 23:05:55,USDT,MATIC,125.564991,addr,tx-dep,Completed\n"
        ),
        encoding="utf-8",
    )
    (raw_dir / "Binance-Withdraw-History-202603230412(UTC--6)_abcd.csv").write_text(
        (
            "Time,Coin,Network,Amount,Fee,Address,TXID,Status\n"
            "23-09-20 22:25:57,HNT,SOL,12.013,0.11,addr,tx-wd,Completed\n"
        ),
        encoding="utf-8",
    )
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        (
            "User ID,Time,Account,Operation,Coin,Change,Remark\n"
            "1,23-08-06 02:34:03,Spot,ETH 2.0 Staking Rewards,BETH,0.00000599,\n"
            "1,23-09-20 18:46:46,Spot,Small Assets Exchange BNB,ETH,-0.00005643,ETH to BNB\n"
            "1,23-09-20 18:46:46,Spot,Small Assets Exchange BNB,BNB,0.00041767,ETH to BNB\n"
            "1,23-09-20 18:17:41,USD-M Futures,Transfer Between Spot Account and UM Futures Account,USDT,-43.90477684,\n"
            "1,23-09-20 18:17:41,Spot,Transfer Between Spot Account and UM Futures Account,USDT,43.90477684,\n"
            "1,21-05-11 00:44:33,Spot,Binance Convert,ETH,0.03158115,\n"
        ),
        encoding="utf-8",
    )
    adapter, profile = build_profile("Binance", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert len(result.canonical_events) == 5
    assert len(result.exceptions) == 3
    kinds = [row["event_kind"] for row in result.canonical_events]
    assert "Trade" in kinds
    assert "Deposit" in kinds
    assert "Withdrawal" in kinds
    assert "Staking" in kinds
    assert any("Transfer Between Spot Account and UM Futures Account" in row["message"] for row in result.exceptions)


def test_binance_historical_ignore_list_only_applies_when_profile_supplies_cutoff_hint(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        (
            "User ID,Time,Account,Operation,Coin,Change,Remark\n"
            "1,23-08-05 08:34:04,Funding,Transfer Between Main and Funding Wallet,USDT,-10,\n"
            "1,23-08-05 08:34:04,Spot,Transfer Between Main and Funding Wallet,USDT,10,\n"
        ),
        encoding="utf-8",
    )

    adapter = source_adapters.get_adapter("Binance")
    profile_without_cutoff = pipeline_common.build_source_profile(
        source="Binance",
        raw_dir=raw_dir,
        adapter_name=adapter.name,
        adapter_supported=adapter.supported,
    )
    profile_with_cutoff = pipeline_common.build_source_profile(
        source="Binance",
        raw_dir=raw_dir,
        adapter_name=adapter.name,
        adapter_supported=adapter.supported,
        normalization_hints={"project_baseline_cutoff_timestamp": "2023-08-05 08:34:04"},
    )

    without_cutoff = adapter.normalize(raw_dir, profile_without_cutoff, exception_decisions={})
    with_cutoff = adapter.normalize(raw_dir, profile_with_cutoff, exception_decisions={})

    assert len(without_cutoff.exceptions) == 2
    assert with_cutoff.exceptions == []
    assert with_cutoff.canonical_events == []


def test_binance_transaction_history_skips_p2p_rows_when_c2c_history_exists(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-C2C-Order-History-202603230441(UTC--6)_abcd.csv").write_text(
        (
            "Order Number,Created Time,Order Type,Asset,Quantity,Total Price,Fiat Type,Counterparty,Status\n"
            "123,23-09-20 19:48:03,SELL,USDT,891,891,CAD,merchant,Completed\n"
        ),
        encoding="utf-8",
    )
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        (
            "User ID,Time,Account,Operation,Coin,Change,Remark\n"
            "1,23-09-20 19:48:03,Funding,P2P Trading,USDT,-891,P2P - 123\n"
        ),
        encoding="utf-8",
    )
    adapter, profile = build_profile("Binance", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert len(result.canonical_events) == 1
    assert result.canonical_events[0]["event_kind"] == "Trade"
    assert len(result.exceptions) == 0


def test_binance_convert_date_updated_covers_transaction_history_one_second_skew(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-Convert-Order-History-202603230441(UTC--6)_abcd.csv").write_text(
        (
            "Time,Wallet,Pair,Type,Sell,Buy,Price,Inverse Price,Date Updated,Status\n"
            "21-05-11 00:44:32,SPOT,ETHBUSD,Instant,124.60184573 BUSD,0.03158115 ETH,x,x,21-05-11 00:44:33,Successful\n"
        ),
        encoding="utf-8",
    )
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        (
            "User ID,Time,Account,Operation,Coin,Change,Remark\n"
            "1,21-05-11 00:44:33,Spot,Binance Convert,ETH,0.03158115,\n"
        ),
        encoding="utf-8",
    )
    adapter, profile = build_profile("Binance", raw_dir)

    result = adapter.normalize(raw_dir, profile, exception_decisions={})

    assert len(result.canonical_events) == 1
    assert len(result.exceptions) == 0


def test_normalize_source_rejects_ambiguous_timezone_inventory(tmp_path: Path) -> None:
    raw_dir = tmp_path / "binance" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "Binance-Spot-Trade-History.csv").write_text(
        (
            "Time,Pair,Side,Price,Executed,Amount,Fee\n"
            "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Timezone validation failed"):
        normalize_source.normalize_source("Binance", raw_dir, tmp_path / "normalized")


def test_normalize_source_cache_invalidates_when_exception_decisions_change(tmp_path: Path) -> None:
    root = tmp_path
    raw_dir = root / "future_exchange" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    out_dir = root / "normalized"

    first = normalize_source.normalize_source("Future Exchange", raw_dir, out_dir)
    summary_path = out_dir / "normalization_summary.json"
    first_summary = pipeline_common.read_profile(summary_path)
    manifest_fingerprint = str(first_summary["manifest_fingerprint"])
    decisions_path = root / "exception_decisions.csv"
    decisions_path.write_text(
        (
            "manifest_fingerprint,event_id,resolution_status,resolution_note\n"
            f"{manifest_fingerprint},generic:adapter_not_implemented,accepted,known gap\n"
        ),
        encoding="utf-8",
    )

    second = normalize_source.normalize_source(
        "Future Exchange",
        raw_dir,
        out_dir,
        exception_decisions=decisions_path,
    )
    second_summary = pipeline_common.read_profile(summary_path)

    assert first["exceptions"] == 1
    assert second["exceptions"] == 0
    assert first_summary["exception_decisions_fingerprint"] != second_summary["exception_decisions_fingerprint"]


def test_normalize_source_uses_current_adapter_support_even_with_stale_profile_json(copy_fixture_tree, tmp_path: Path) -> None:
    root = tmp_path
    raw_dir = copy_fixture_tree("raw_sources/wealthsimple_renamed/raw", destination_name="wealthsimple_raw")
    out_dir = root / "normalized"
    profile_json = root / "profile.json"
    profile_json.write_text(
        (
            '{\n'
            '  "manifest_fingerprint": "stale",\n'
            '  "adapter": "wealthsimple",\n'
            '  "adapter_supported": false\n'
            '}\n'
        ),
        encoding="utf-8",
    )

    summary = normalize_source.normalize_source(
        "WealthSimple",
        raw_dir,
        out_dir,
        profile_json=profile_json,
        force=True,
    )

    assert summary["adapter_supported"]
    assert summary["status"] == "ready"
    assert summary["manifest_fingerprint"] != "stale"


def test_normalize_source_applies_explicit_normalization_window_overrides(tmp_path: Path) -> None:
    root = tmp_path
    raw_dir = root / "binance" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "Binance-Deposit-History-202603230411(UTC--6)_abcd.csv").write_text(
        (
            "Time,Coin,Network,Amount,Address,TXID,Status\n"
            "23-08-05 08:34:05,USDT,MATIC,10,addr,tx-1,Completed\n"
            "26-01-01 00:00:00,USDT,MATIC,20,addr,tx-2,Completed\n"
        ),
        encoding="utf-8",
    )
    out_dir = root / "normalized"

    summary = normalize_source.normalize_source(
        "Binance",
        raw_dir,
        out_dir,
        window_start="2023-08-05 08:34:05",
        window_end="2025-12-31 23:59:59",
    )

    events = pipeline_common.read_profile(out_dir / "normalization_summary.json")
    canonical_rows = (out_dir / "canonical_events.csv").read_text(encoding="utf-8")

    assert summary["canonical_events"] == 1
    assert summary["events_outside_normalization_window"] == 1
    assert events["normalization_window_start"] == "2023-08-05 08:34:05"
    assert events["normalization_window_end"] == "2025-12-31 23:59:59"
    assert "2023-08-05 14:34:05" in canonical_rows
    assert "2026-01-01" not in canonical_rows


def test_normalize_source_cache_invalidates_when_profile_hints_change_adapter_behavior(tmp_path: Path) -> None:
    root = tmp_path
    raw_dir = root / "binance" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        (
            "User ID,Time,Account,Operation,Coin,Change,Remark\n"
            "1,23-08-05 08:34:04,Funding,Transfer Between Main and Funding Wallet,USDT,-10,\n"
            "1,23-08-05 08:34:04,Spot,Transfer Between Main and Funding Wallet,USDT,10,\n"
        ),
        encoding="utf-8",
    )
    out_dir = root / "normalized"
    profile_without_cutoff = root / "profile_without_cutoff.json"
    profile_with_cutoff = root / "profile_with_cutoff.json"
    profile_without_cutoff.write_text(json.dumps({"normalization_hints": {}}), encoding="utf-8")
    profile_with_cutoff.write_text(
        json.dumps({"normalization_hints": {"project_baseline_cutoff_timestamp": "2023-08-05 08:34:04"}}),
        encoding="utf-8",
    )

    first = normalize_source.normalize_source(
        "Binance",
        raw_dir,
        out_dir,
        profile_json=profile_without_cutoff,
    )
    second = normalize_source.normalize_source(
        "Binance",
        raw_dir,
        out_dir,
        profile_json=profile_with_cutoff,
    )

    assert first["status"] == "needs_review"
    assert first["exceptions"] == 2
    assert second["status"] == "ready"
    assert second["exceptions"] == 0
