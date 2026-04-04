from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.shakepay.translation import translate_row
from tallylot.adapters.support import CsvRowContext
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import EconomicKind, ProjectionHint
from tests.support.adapter_packs import fixture_raw_dir, profile_and_adapter


def test_shakepay_buy_row_uses_fiat_value_when_debit_columns_are_blank() -> None:
    profile, _ = profile_and_adapter(
        "Shakepay", fixture_raw_dir("shakepay", "cash_crypto_mix")
    )

    parsed = translate_row(
        profile,
        CsvRowContext(
            path=Path("crypto_transactions_summary.csv"),
            row_index=2,
            row={
                "Date": "2025-05-11 20:56:06",
                "Amount Debited": "",
                "Asset Debited": "",
                "Amount Credited": "0.00001562",
                "Asset Credited": "BTC",
                "Market Value": "1.32",
                "Market Value Currency": "CAD",
                "Book Cost": "1.32",
                "Book Cost Currency": "CAD",
                "Type": "Buy",
                "Description": "Bought @ generic rate",
            },
        ),
    )

    assert parsed is not None
    assert not isinstance(parsed, IssueRecord)
    facts = compile_activity_drafts((parsed,))

    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.SPOT_TRADE
    assert [str(leg.instrument_id) for leg in facts[0].legs] == [
        "symbol:BTC",
        "symbol:CAD",
    ]
    assert [str(leg.quantity) for leg in facts[0].legs] == ["0.00001562", "-1.32"]


def test_shakepay_sell_row_uses_fiat_value_when_credit_columns_are_blank() -> None:
    profile, _ = profile_and_adapter(
        "Shakepay", fixture_raw_dir("shakepay", "cash_crypto_mix")
    )

    parsed = translate_row(
        profile,
        CsvRowContext(
            path=Path("crypto_transactions_summary.csv"),
            row_index=2,
            row={
                "Date": "2025-02-22 02:27:20",
                "Amount Debited": "0.05298092265",
                "Asset Debited": "ETH",
                "Amount Credited": "",
                "Asset Credited": "",
                "Market Value": "203.27",
                "Market Value Currency": "CAD",
                "Book Cost": "199.99",
                "Book Cost Currency": "CAD",
                "Type": "Sell",
                "Description": "Sold @ generic rate",
            },
        ),
    )

    assert parsed is not None
    assert not isinstance(parsed, IssueRecord)
    facts = compile_activity_drafts((parsed,))

    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.SPOT_TRADE
    assert [str(leg.instrument_id) for leg in facts[0].legs] == [
        "symbol:CAD",
        "symbol:ETH",
    ]
    assert [str(leg.quantity) for leg in facts[0].legs] == ["203.27", "-0.05298092265"]


def test_shakepay_receive_row_normalizes_as_inbound_transfer() -> None:
    profile, _ = profile_and_adapter(
        "Shakepay", fixture_raw_dir("shakepay", "cash_crypto_mix")
    )

    parsed = translate_row(
        profile,
        CsvRowContext(
            path=Path("crypto_transactions_summary.csv"),
            row_index=2,
            row={
                "Date": "2025-02-10 23:45:01",
                "Amount Debited": "",
                "Asset Debited": "",
                "Amount Credited": "0.001",
                "Asset Credited": "ETH",
                "Market Value": "3.85",
                "Market Value Currency": "CAD",
                "Book Cost": "3.84698331",
                "Book Cost Currency": "CAD",
                "Type": "Receive",
                "Description": "External wallet receive",
            },
        ),
    )

    assert parsed is not None
    assert not isinstance(parsed, IssueRecord)
    facts = compile_activity_drafts((parsed,))

    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.CHAIN_TRANSFER_IN
    assert facts[0].projection_hint == ProjectionHint.DEPOSIT
    assert [str(leg.instrument_id) for leg in facts[0].legs] == ["symbol:ETH"]
    assert [str(leg.quantity) for leg in facts[0].legs] == ["0.001"]
