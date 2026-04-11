from __future__ import annotations

import json

import pytest

from tallylot.domain.locations import LocationKind, LocationRecord
from tallylot.domain.types import LocationId


def test_location_record_to_row_serializes_parent_and_path() -> None:
    record = LocationRecord(
        location_id=LocationId("coinbase:primary:wallet"),
        location_kind=LocationKind.SUBACCOUNT,
        label="Wallet",
        parent_location_id=LocationId("coinbase:primary"),
        path=("primary", "wallet"),
    )

    row = record.to_row()

    assert row["location_kind"] == "subaccount"
    assert row["parent_location_id"] == "coinbase:primary"
    assert json.loads(row["path"]) == ["primary", "wallet"]


def test_location_record_rejects_blank_label() -> None:
    with pytest.raises(ValueError, match="location label must not be blank"):
        LocationRecord(
            location_id=LocationId("coinbase:primary"),
            location_kind=LocationKind.ACCOUNT,
            label=" ",
        )


def test_location_record_rejects_blank_path_segment() -> None:
    with pytest.raises(ValueError, match="location path segments must not be blank"):
        LocationRecord(
            location_id=LocationId("coinbase:primary:wallet"),
            location_kind=LocationKind.SUBACCOUNT,
            label="Wallet",
            parent_location_id=LocationId("coinbase:primary"),
            path=("primary", " "),
        )
