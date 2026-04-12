from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest

from tallylot.adapters.sources.explorers.ronin.translation.rows import (
    RoninRawRow,
    RoninSummaryRow,
    infer_summary_utc_timestamp,
    is_supported_restake_pair,
    parse_raw_row,
    parse_summary_row,
    summary_time_calibrations,
)


def _raw_row(*, tx_hash: str = "0xraw") -> RoninRawRow:
    return RoninRawRow(
        path_name="ronin-tx.csv",
        row_index=2,
        tx_hash=tx_hash,
        timestamp=datetime(2022, 1, 13, 20, 24, 56, tzinfo=UTC),
        from_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        to_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        method="transfer",
        asset_symbol="AXS",
        inbound_quantity=Decimal("1.0"),
        outbound_quantity=Decimal("0"),
        fee_text="0.000000",
        fee=Decimal("0"),
        status="success",
    )


def _summary_row(**overrides: object) -> RoninSummaryRow:
    data: dict[str, object] = {
        "path_name": "ronin-summary.csv",
        "row_index": 2,
        "tx_hash": "0xsummary",
        "local_timestamp": datetime(2022, 1, 13, 13, 24, 56),
        "action_type": "transfer",
        "ronin_address": "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        "from_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "to_address": "0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        "asset_symbol": "AXS",
        "quantity": Decimal("0.195"),
    }
    data.update(overrides)
    return RoninSummaryRow(**cast(Any, data))


@pytest.mark.parametrize(
    "row",
    [
        {
            "Txhash": "0xraw",
            "DateTime": "not-a-timestamp",
            "From": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "To": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "Method": "transfer",
            "Token / Collectibles": "Axie Infinity Shard",
            "Value in": "1.0",
            "Value out": "0",
            "TxnFee(RON)": "0.000000",
            "Status": "Success",
        },
        {
            "Txhash": "",
            "DateTime": "2022-01-13 20:24:56",
            "From": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "To": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "Method": "transfer",
            "Token / Collectibles": "Axie Infinity Shard",
            "Value in": "1.0",
            "Value out": "0",
            "TxnFee(RON)": "0.000000",
            "Status": "Success",
        },
        {
            "Txhash": "0xraw",
            "DateTime": "2022-01-13 20:24:56",
            "From": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "To": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "Method": "transfer",
            "Token / Collectibles": "",
            "Value in": "1.0",
            "Value out": "0",
            "TxnFee(RON)": "0.000000",
            "Status": "Success",
        },
    ],
)
def test_parse_raw_row_rejects_invalid_input(row: dict[str, str]) -> None:
    assert parse_raw_row("ronin-tx.csv", 2, row) is None


def test_parse_summary_row_supports_secondary_asset_columns() -> None:
    row = parse_summary_row(
        "ronin-summary.csv",
        2,
        {
            "RoninAddress": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            "TxnHash": "0xsummary",
            "Timestamp": "13/01/2022, 13:24:56",
            "ActionType": "transfer",
            "AXS": "0",
            "RON": "2.5000000000",
            "From": "ronin:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "To": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        },
    )

    assert row is not None
    assert row.asset_symbol == "RON"
    assert row.quantity == Decimal("2.5")


@pytest.mark.parametrize(
    "row",
    [
        {
            "RoninAddress": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            "TxnHash": "0xsummary",
            "Timestamp": "not-a-timestamp",
            "ActionType": "transfer",
            "AXS": "0.1950000000",
            "From": "ronin:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "To": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        },
        {
            "RoninAddress": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            "TxnHash": "0xsummary",
            "Timestamp": "13/01/2022, 13:24:56",
            "ActionType": "transfer",
            "AXS": "0",
            "RON": "0",
            "SLP": "0",
            "USDC": "0",
            "ETH": "0",
            "From": "ronin:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "To": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        },
        {
            "RoninAddress": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
            "TxnHash": "",
            "Timestamp": "13/01/2022, 13:24:56",
            "ActionType": "transfer",
            "AXS": "0.1950000000",
            "From": "ronin:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "To": "ronin:1b1953d5124442b879e3dfc6b9c413d0a8c03e94",
        },
    ],
)
def test_parse_summary_row_rejects_invalid_input(row: dict[str, str]) -> None:
    assert parse_summary_row("ronin-summary.csv", 2, row) is None


def test_summary_time_calibrations_skip_unmatched_rows_and_deduplicate() -> None:
    local_timestamp = datetime(2022, 1, 13, 13, 24, 56)
    raw_groups_by_hash: dict[str, tuple[RoninRawRow, ...]] = {
        "0xsummary": (_raw_row(tx_hash="0xsummary"),),
    }
    summary_rows = (
        _summary_row(tx_hash="0xsummary", local_timestamp=local_timestamp),
        _summary_row(tx_hash="0xsummary", local_timestamp=local_timestamp, row_index=3),
        _summary_row(
            tx_hash="0xunmatched",
            local_timestamp=local_timestamp,
            row_index=4,
        ),
    )

    calibrations = summary_time_calibrations(raw_groups_by_hash, summary_rows)

    assert calibrations == ((local_timestamp, timedelta(hours=7)),)


def test_infer_summary_utc_timestamp_chooses_nearest_calibration() -> None:
    local_timestamp = datetime(2022, 1, 13, 13, 27, 56)
    calibrations = (
        (datetime(2022, 1, 13, 13, 24, 56), timedelta(hours=7)),
        (datetime(2022, 1, 13, 13, 57, 56), timedelta(hours=8)),
    )

    assert infer_summary_utc_timestamp(local_timestamp, calibrations) == datetime(
        2022, 1, 13, 20, 27, 56, tzinfo=UTC
    )
    assert infer_summary_utc_timestamp(local_timestamp, ()) is None


def test_is_supported_restake_pair_rejects_missing_rows() -> None:
    positive_row = _summary_row(
        tx_hash="0xrestake",
        local_timestamp=datetime(2022, 1, 13, 13, 24, 56),
        asset_symbol="AXS",
        quantity=Decimal("0.0277578354"),
    )

    assert not is_supported_restake_pair(
        None,
        positive_row,
        {"0x1b1953d5124442b879e3dfc6b9c413d0a8c03e94"},
    )
