from __future__ import annotations

from decimal import Decimal

import pytest

from tallylot.domain.assertion import (
    LocationValue,
    MoneyValue,
    OwnerValue,
    QuantityValue,
    assertion_value_fingerprint,
    assertion_value_json,
    assertion_value_payload,
)


def test_quantity_value_preserves_decimal_and_subject_payload() -> None:
    value = QuantityValue(
        quantity=Decimal("1.2500"),
        subject_ref=(
            "position",
            (
                ("beneficial_owner",),
                ("location",),
                ("instrument",),
                None,
                "held_position",
            ),
        ),
    )

    assert value.to_payload() == {
        "assertion_value_kind": "quantity",
        "quantity": "1.25",
        "subject_ref": [
            "position",
            [
                ["beneficial_owner"],
                ["location"],
                ["instrument"],
                None,
                "held_position",
            ],
        ],
    }
    assert assertion_value_payload(value) == [
        "quantity",
        [
            "1.25",
            [
                "position",
                [
                    ["beneficial_owner"],
                    ["location"],
                    ["instrument"],
                    None,
                    "held_position",
                ],
            ],
        ],
    ]


def test_assertion_value_fingerprint_is_stable_for_semantically_equal_payloads() -> (
    None
):
    first = MoneyValue(amount=Decimal("10.00"), currency="USD")
    second = MoneyValue(amount=Decimal("10"), currency="USD")

    assert first == second
    assert assertion_value_json(first) == assertion_value_json(second)
    assert assertion_value_fingerprint(first) == assertion_value_fingerprint(second)


def test_assertion_values_emit_canonical_tuples() -> None:
    quantity_value = QuantityValue(
        quantity=Decimal("2.500"),
        subject_ref=(
            "position",
            (("owner:1",), ("location:1",), ("btc",), None, "held_position"),
        ),
    )
    money_value = MoneyValue(amount=Decimal("10.00"), currency="USD")
    owner_value = OwnerValue(beneficial_owner_ref="owner:filing")
    location_value = LocationValue(location_ref="location:coinbase")

    assert quantity_value.canonical_tuple() == (
        "quantity",
        (
            "2.5",
            ["position", [["owner:1"], ["location:1"], ["btc"], None, "held_position"]],
        ),
    )
    assert money_value.canonical_tuple() == ("money", ("10", "USD"))
    assert owner_value.canonical_tuple() == ("owner", ("", "owner:filing", ""))
    assert location_value.canonical_tuple() == ("location", ("location:coinbase",))


def test_owner_and_location_values_emit_canonical_serialization() -> None:
    owner_value = OwnerValue(beneficial_owner_ref="owner:filing")
    location_value = LocationValue(location_ref="location:coinbase")

    assert owner_value.to_payload()["beneficial_owner_ref"] == "owner:filing"
    assert location_value.to_payload() == {
        "assertion_value_kind": "location",
        "location_ref": "location:coinbase",
    }


def test_owner_value_requires_at_least_one_owner_reference() -> None:
    with pytest.raises(
        ValueError, match="owner value requires at least one owner reference"
    ):
        OwnerValue()


def test_location_value_requires_location_ref() -> None:
    with pytest.raises(ValueError, match="location value requires location_ref"):
        LocationValue(location_ref="")
