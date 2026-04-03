from __future__ import annotations

import pytest

import normalization_common


def test_attach_fee_to_event_sets_fee_fields() -> None:
    event = {
        "event_id": "evt-1",
        "fee_amount": "",
        "fee_asset": "",
    }

    updated = normalization_common.attach_fee_to_event(event, fee_amount="0.123", fee_asset="eth")

    assert updated["fee_amount"] == "0.12300000"
    assert updated["fee_asset"] == "ETH"
    assert event["fee_amount"] == ""


def test_attach_fee_to_event_list_requires_single_unambiguous_event() -> None:
    events = [
        {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
        {"event_id": "evt-2", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
    ]

    with pytest.raises(ValueError, match="single unambiguous target event"):
        normalization_common.attach_fee_to_event_list(
            events,
            fee_amount="0.5",
            fee_asset="bnb",
            timestamp="2024-01-01 00:00:00",
        )


def test_attach_fee_to_event_rejects_conflicting_fee() -> None:
    event = {
        "event_id": "evt-1",
        "fee_amount": "0.10000000",
        "fee_asset": "ETH",
    }

    with pytest.raises(ValueError, match="conflicting fee"):
        normalization_common.attach_fee_to_event(event, fee_amount="0.2", fee_asset="ETH")


def test_attach_fee_to_event_list_attaches_to_named_event() -> None:
    events = [
        {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
        {"event_id": "evt-2", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
    ]

    updated = normalization_common.attach_fee_to_event_list(
        events,
        fee_amount="0.5",
        fee_asset="bnb",
        target_event_id="evt-2",
    )

    assert updated[0]["fee_amount"] == ""
    assert updated[1]["fee_amount"] == "0.50000000"
    assert updated[1]["fee_asset"] == "BNB"


def test_attach_fee_to_event_list_supports_optional_timestamp_tolerance() -> None:
    events = [
        {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:01", "fee_amount": "", "fee_asset": ""},
    ]

    updated = normalization_common.attach_fee_to_event_list(
        events,
        fee_amount="0.5",
        fee_asset="bnb",
        timestamp="2024-01-01 00:00:00",
        timestamp_tolerance_seconds=1,
    )

    assert updated[0]["fee_amount"] == "0.50000000"


def test_attach_fee_to_event_list_emits_standalone_when_match_is_ambiguous() -> None:
    events = [
        {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
        {"event_id": "evt-2", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
    ]
    standalone = {
        "event_id": "fee-1",
        "timestamp": "2024-01-01 00:00:00",
        "event_kind": "Other Fee",
        "amount_out": "0.50000000",
        "asset_out": "BNB",
    }

    updated = normalization_common.attach_fee_to_event_list(
        events,
        fee_amount="0.5",
        fee_asset="bnb",
        timestamp="2024-01-01 00:00:00",
        standalone_event=standalone,
    )

    assert len(updated) == 3
    assert updated[-1]["event_id"] == "fee-1"


def test_attach_fee_to_event_list_rejects_mismatched_standalone_fee_event() -> None:
    events = [
        {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
        {"event_id": "evt-2", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
    ]
    standalone = {
        "event_id": "fee-1",
        "timestamp": "2024-01-01 00:00:00",
        "event_kind": "Other Fee",
        "amount_out": "999.00000000",
        "asset_out": "WRONG",
    }

    with pytest.raises(ValueError, match="Standalone fee event must match"):
        normalization_common.attach_fee_to_event_list(
            events,
            fee_amount="0.5",
            fee_asset="bnb",
            timestamp="2024-01-01 00:00:00",
            standalone_event=standalone,
        )
