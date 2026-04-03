from __future__ import annotations

import reconcile_source


def expected_row(**overrides: str) -> dict[str, str]:
    row = {
        "Type": "Trade",
        "Buy": "0.00175640",
        "Buy Cur.": "BTC",
        "Sell": "25.00000000",
        "Sell Cur.": "CAD",
        "Fee": "1.46965254",
        "Fee Cur.": "CAD",
        "Exchange": "Coinbase",
        "Group": "",
        "Comment": "Bought 0.0017564 BTC for $25.00 CAD",
        "Date": "2019-09-11 01:06:35",
        "Tx-ID": "coinbase-retail-buy-1",
        "canonical_event_id": "evt-1",
        "confidence": "high",
        "status": "mapped",
        "raw_file": "coinbase.csv",
        "raw_row_ref": "buy-1",
        "render_match_window_seconds": "20",
        "render_fee_tolerance": "0.03000000",
        "render_comment_mode": "exact",
        "render_tx_id_mode": "ignore",
        "render_allowed_types": "Trade",
        "render_notes": "",
    }
    row.update(overrides)
    return row


def actual_row(**overrides: str) -> dict[str, str]:
    row = {
        "Type": "Trade",
        "Buy": "0.00175640",
        "Buy Cur.": "BTC",
        "Sell": "25.00000000",
        "Sell Cur.": "CAD",
        "Fee": "1.49000000",
        "Fee Cur.": "CAD",
        "Exchange": "Coinbase",
        "Group": "",
        "Comment": "Bought 0.0017564 BTC for $25.00 CAD",
        "Date": "2019-09-11 01:06:26",
        "Tx-ID": "",
    }
    row.update(overrides)
    return row


def test_compare_transactions_flags_extra_synthetic_row() -> None:
    expected = [expected_row()]
    actual = [
        actual_row(),
        {
            "Type": "Deposit",
            "Buy": "25.00000000",
            "Buy Cur.": "CAD",
            "Sell": "",
            "Sell Cur.": "",
            "Fee": "0.00000000",
            "Fee Cur.": "",
            "Exchange": "Coinbase",
            "Group": "",
            "Comment": "",
            "Date": "2019-09-11 01:06:26",
            "Tx-ID": "",
        },
    ]

    results = reconcile_source.compare_transactions(actual, expected)

    assert len(results["matched"]) == 1
    assert len(results["extra"]) == 1
    assert results["extra"][0]["Type"] == "Deposit"


def test_compare_balances_reports_asset_deltas() -> None:
    deltas = reconcile_source.compare_balances(
        [
            {"Amount": "1.00000000", "Currency": "BTC", "Exchange": "Coinbase"},
            {"Amount": "0.50000000", "Currency": "ETH", "Exchange": "Coinbase"},
        ],
        [
            {"source": "Coinbase", "balance_kind": "asset_balance", "asset": "BTC", "quantity": "1.00000000"},
            {"source": "Coinbase", "balance_kind": "asset_balance", "asset": "ETH", "quantity": "0.40000000"},
        ],
        "Coinbase",
    )

    eth_row = next(row for row in deltas if row["asset"] == "ETH")
    assert eth_row["status"] == "delta"
    assert eth_row["difference"] == "0.10000000"


def test_compare_transactions_accepts_exchange_aliases() -> None:
    expected = [expected_row()]
    actual = [actual_row(Exchange="Coinbase Pro")]

    results = reconcile_source.compare_transactions(
        actual,
        expected,
        allowed_exchanges={"Coinbase", "Coinbase Pro"},
    )

    assert len(results["matched"]) == 1
    assert results["missing"] == []
