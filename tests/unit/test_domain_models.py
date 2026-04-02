from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from crypto_reconciliation.domain.models import CanonicalEvent
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, SourceId


def _valid_canonical_event() -> CanonicalEvent:
    return CanonicalEvent(
        event_id=EventId("event-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        account="Fixture",
        wallet="Primary",
        timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
        event_kind="Trade",
        asset_in=AssetSymbol("BTC"),
        amount_in=Decimal("1"),
    )


def test_canonical_event_rejects_incomplete_asset_amount_pairs() -> None:
    with pytest.raises(ValueError, match="asset_in and amount_in must both be present"):
        replace(_valid_canonical_event(), amount_in=None)

    with pytest.raises(ValueError, match="asset_out and amount_out must both be present"):
        replace(_valid_canonical_event(), asset_out=AssetSymbol("CAD"))

    with pytest.raises(ValueError, match="fee_asset and fee_amount must both be present"):
        replace(_valid_canonical_event(), fee_amount=Decimal("0.1"))


def test_canonical_event_rejects_non_positive_amounts() -> None:
    with pytest.raises(ValueError, match="amount_in must be greater than zero"):
        replace(_valid_canonical_event(), amount_in=Decimal("0"))

    with pytest.raises(ValueError, match="amount_out must be greater than zero"):
        replace(
            _valid_canonical_event(),
            asset_in=None,
            amount_in=None,
            asset_out=AssetSymbol("CAD"),
            amount_out=Decimal("-10"),
        )

    with pytest.raises(ValueError, match="fee_amount must be greater than zero"):
        replace(_valid_canonical_event(), fee_asset=AssetSymbol("CAD"), fee_amount=Decimal("0"))
