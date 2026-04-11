from __future__ import annotations

import pytest
from typing import NamedTuple

from tallylot.domain.location_identifiers import (
    location_id_from_identifier,
    location_id_from_parts,
    normalized_identifier,
    require_location_id,
    scope_token_for_identifier,
)


class LocationIdentifierCase(NamedTuple):
    identifier_kind: str
    identifier_value: str
    network_scope: str
    suffix: tuple[str, ...]
    expected: str


def test_location_id_from_parts_normalizes_generic_segments() -> None:
    assert str(location_id_from_parts("binance", "spot")) == "binance:spot"
    assert str(location_id_from_parts("crypto.com")) == "crypto.com"
    assert str(location_id_from_parts("  Binance  ", "Spot Trading!")) == (
        "binance:spot_trading"
    )


@pytest.mark.parametrize(
    "case",
    (
        LocationIdentifierCase(
            "evm_address",
            "0x1111111111111111111111111111111111111111",
            "ethereum",
            (),
            "evm:ethereum:0x1111111111111111111111111111111111111111",
        ),
        LocationIdentifierCase(
            "near_account",
            "example.near",
            "",
            (),
            "near:example.near",
        ),
        LocationIdentifierCase(
            "btc_address",
            "bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs",
            "",
            (),
            "bitcoin:bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs",
        ),
        LocationIdentifierCase(
            "solana_address",
            "11111111111111111111111111111111",
            "",
            (),
            "solana:11111111111111111111111111111111",
        ),
        LocationIdentifierCase(
            "tron_address",
            "TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "",
            (),
            "tron:TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        ),
    ),
)
def test_location_id_from_identifier_builds_rooted_onchain_ids(
    case: LocationIdentifierCase,
) -> None:
    assert (
        str(
            location_id_from_identifier(
                case.identifier_kind,
                case.identifier_value,
                network_scope=case.network_scope,
                suffix=case.suffix,
            )
        )
        == case.expected
    )


def test_location_id_from_identifier_normalizes_suffix_segments() -> None:
    assert (
        str(
            location_id_from_identifier(
                "near_account",
                "example.near",
                suffix=("staking rewards",),
            )
        )
        == "near:example.near:staking_rewards"
    )


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    (
        ("coinbase:primary", "coinbase:primary"),
        ("crypto.com", "crypto.com"),
        ("near:example.near", "near:example.near"),
        (
            "evm:ethereum:0x1111111111111111111111111111111111111111",
            "evm:ethereum:0x1111111111111111111111111111111111111111",
        ),
        (
            "bitcoin:bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs",
            "bitcoin:bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs",
        ),
    ),
)
def test_require_location_id_accepts_supported_location_id_forms(
    raw_value: str,
    expected: str,
) -> None:
    assert str(require_location_id(raw_value, label="location id")) == expected


@pytest.mark.parametrize(
    "raw_value",
    (
        "manual-balance-smoke:primary",
        "fixture:wallet-1",
        "crypto-com",
    ),
)
def test_require_location_id_rejects_hyphenated_generic_location_ids(
    raw_value: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="manual balance row location_id .*is not a supported location id",
    ):
        require_location_id(raw_value, label="manual balance row location_id")


def test_location_id_from_parts_rejects_blank_parts() -> None:
    with pytest.raises(ValueError, match="location_id parts must not be blank"):
        location_id_from_parts(" ", "spot")


def test_normalized_identifier_preserves_non_evm_values() -> None:
    assert normalized_identifier("evm_address", "0xABCDEF") == "0xabcdef"
    assert normalized_identifier("btc_address", "bc1qexample") == "bc1qexample"


def test_scope_token_for_identifier_uses_supported_networks() -> None:
    assert scope_token_for_identifier("0x1111111111111111111111111111111111111111") == (
        "evm:0x1111111111111111111111111111111111111111"
    )
    assert scope_token_for_identifier("TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA") == (
        "tron:TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    assert scope_token_for_identifier("unsupported") == ""
