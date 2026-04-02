from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from crypto_reconciliation.adapters.sources.mapped_event_support import MappedEventSpec, mapped_event
from crypto_reconciliation.adapters.sources.wallet_record_support import normalized_identifier, wallet_identifier_kind


def test_mapped_event_preserves_internal_canonical_fields() -> None:
    event = mapped_event(
        MappedEventSpec(
            event_id="evt-1",
            source="fixture",
            adapter_id="fixture_adapter",
            account="Primary",
            wallet="Primary",
            timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
            event_kind="Deposit",
            description="Fixture deposit",
            raw_file="fixture.csv",
            raw_row_ref="row:2",
            asset_in="BTC",
            amount_in=Decimal("1.5"),
        )
    )

    assert event.event_kind == "Deposit"
    assert event.description == "Fixture deposit"
    assert str(event.asset_in) == "BTC"


def test_wallet_identifier_helpers_normalize_evm_and_classify_near_accounts() -> None:
    assert normalized_identifier("evm_address", "0xABCDEF") == "0xabcdef"
    assert wallet_identifier_kind("example.near") == "near_account"
