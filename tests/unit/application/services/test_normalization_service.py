from __future__ import annotations

import json
from pathlib import Path

import pytest

from crypto_reconciliation.application.models.source import NormalizeRequest
from crypto_reconciliation.infrastructure.serialization.csv_io import read_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tests.support.services import build_normalization_service


def test_normalization_service_filters_events_outside_explicit_window(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
            "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
            "2023-08-04 10:00:00,trade,BTC,1.0,CAD,10.0,CAD,0.1,tx-early,early,Fixture,Primary\n"
            "2023-08-06 10:00:00,trade,ETH,2.0,CAD,20.0,CAD,0.2,tx-keep,keep,Fixture,Primary\n"
        ),
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_dir=raw_dir,
            output_dir=output_dir,
            window_start="2023-08-05 08:34:05",
            window_end="2025-12-31 23:59:59",
        )
    )

    canonical_rows = read_rows(output_dir / "transactions.csv")
    summary = json.loads((output_dir / "normalization_summary.json").read_text(encoding="utf-8"))
    profile = json.loads((output_dir / "profile.json").read_text(encoding="utf-8"))

    assert response.transaction_count == 1
    assert len(canonical_rows) == 1
    assert canonical_rows[0]["tx_hash"] == "tx-keep"
    assert summary["transaction_count"] == 1
    assert summary["transactions_outside_normalization_window"] == 1
    assert summary["normalization_window_start"] == "2023-08-05 08:34:05"
    assert summary["normalization_window_end"] == "2025-12-31 23:59:59"
    assert profile["normalization_hints"]["normalization_window_start"] == "2023-08-05 08:34:05"
    assert profile["normalization_hints"]["normalization_window_end"] == "2025-12-31 23:59:59"


def test_normalization_service_filters_timestamped_issues_outside_explicit_window(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-08-05 08:34:04,Funding,Transfer Between Main and Funding Wallet,USDT,-10,\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="Binance",
            raw_dir=raw_dir,
            output_dir=output_dir,
            window_start="2023-08-05 08:34:05",
            window_end="2025-12-31 23:59:59",
        )
    )

    issue_rows = read_rows(output_dir / "exceptions.csv")
    summary = json.loads((output_dir / "normalization_summary.json").read_text(encoding="utf-8"))

    assert response.issue_count == 0
    assert not issue_rows
    assert summary["issue_count"] == 0
    assert summary["issues_outside_normalization_window"] == 1


def test_normalization_service_filters_row_scoped_issues_outside_explicit_window(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "activity.csv").write_text(
        "transaction_date,settlement_date,account_id,account_type,activity_type,activity_sub_type,"
        "quantity,currency,symbol,commission,net_cash_amount\n"
        "2023-09-22,2023-09-22,acct-1,Crypto,staking_reward,REWARD,0.05,CAD,BTC,0,0\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="Future Broker",
            raw_dir=raw_dir,
            output_dir=output_dir,
            window_start="2023-09-23 00:00:00",
            window_end="2025-12-31 23:59:59",
        )
    )

    issue_rows = read_rows(output_dir / "exceptions.csv")
    summary = json.loads((output_dir / "normalization_summary.json").read_text(encoding="utf-8"))

    assert response.issue_count == 0
    assert not issue_rows
    assert summary["issue_count"] == 0
    assert summary["issues_outside_normalization_window"] == 1


def test_normalization_service_rejects_ambiguous_timezone_inventory(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Binance-Spot-Trade-History.csv").write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n",
        encoding="utf-8",
    )
    service = build_normalization_service()

    with pytest.raises(ValueError, match="timezone issues"):
        service.execute(
            NormalizeRequest(
                source="Binance",
                raw_dir=raw_dir,
                output_dir=tmp_path / "normalized",
            )
        )


def test_normalization_service_rewrites_stale_output_profile_with_live_adapter_state(tmp_path: Path) -> None:
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
    output_dir = tmp_path / "normalized"
    output_dir.mkdir()
    (output_dir / "profile.json").write_text(
        json.dumps(
            {
                "manifest_fingerprint": "stale",
                "adapter_id": "generic",
                "supported": False,
            }
        ),
        encoding="utf-8",
    )
    service = build_normalization_service()

    response = service.execute(
        NormalizeRequest(
            source="Future Exchange",
            raw_dir=raw_dir,
            output_dir=output_dir,
        )
    )
    profile = json.loads((output_dir / "profile.json").read_text(encoding="utf-8"))

    assert response.adapter_id == "coinbase"
    assert profile["adapter_id"] == "coinbase"
    assert profile["supported"] is True
    assert profile["manifest_fingerprint"] != "stale"
