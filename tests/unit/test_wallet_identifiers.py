from __future__ import annotations

from tallylot.domain.location_identifiers import (
    identifier_kind_for_value,
    normalized_identifier,
    scope_token_for_identifier,
)


def test_identifier_kind_for_value_detects_supported_formats() -> None:
    assert (
        identifier_kind_for_value("0x1111111111111111111111111111111111111111")
        == "evm_address"
    )
    assert (
        identifier_kind_for_value("TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        == "tron_address"
    )
    assert (
        identifier_kind_for_value("bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        == "btc_address"
    )


def test_identifier_kind_for_value_detects_cardano_and_near_values() -> None:
    assert (
        identifier_kind_for_value(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        == "cardano_account_key"
    )
    assert identifier_kind_for_value("alice.near") == "near_account"


def test_normalized_identifier_lowercases_only_evm_addresses() -> None:
    assert normalized_identifier("evm_address", "0xABCD") == "0xabcd"
    assert normalized_identifier("btc_address", "bc1qexample") == "bc1qexample"


def test_scope_token_for_identifier_uses_network_specific_prefixes() -> None:
    assert scope_token_for_identifier("0x1111111111111111111111111111111111111111") == (
        "evm:0x1111111111111111111111111111111111111111"
    )
    assert scope_token_for_identifier("TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA") == (
        "tron:TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    assert scope_token_for_identifier("unsupported") == ""


def test_scope_token_for_identifier_does_not_emit_tokens_for_broad_near_matches() -> (
    None
):
    assert scope_token_for_identifier("alice.near") == ""
