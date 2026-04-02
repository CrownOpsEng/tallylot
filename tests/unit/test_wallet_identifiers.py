from __future__ import annotations

from crypto_reconciliation.domain.wallet_identifiers import (
    normalized_identifier,
    scope_token_for_identifier,
    wallet_identifier_kind,
)


def test_wallet_identifier_kind_detects_supported_wallet_formats() -> None:
    assert wallet_identifier_kind("0x1111111111111111111111111111111111111111") == "evm_address"
    assert wallet_identifier_kind("TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA") == "tron_address"
    assert wallet_identifier_kind("bc1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") == "btc_address"


def test_wallet_identifier_kind_detects_cardano_and_near_values() -> None:
    assert (
        wallet_identifier_kind(
            "5ebb4c94284e7c805f247a6c7fbbb705bf3c1a234889401321c351aa05d468b6"
            "ddb9577f143d435ea4bba178a611110f309c930e5400ac960b4bed9e912f2825"
        )
        == "cardano_account_key"
    )
    assert wallet_identifier_kind("alice.near") == "near_account"


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


def test_scope_token_for_identifier_does_not_emit_tokens_for_broad_near_matches() -> None:
    assert scope_token_for_identifier("alice.near") == ""
