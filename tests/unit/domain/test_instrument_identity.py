from __future__ import annotations

from tallylot.domain.instruments import (
    InstrumentIdentityClaim,
    InstrumentKind,
    asset_claim,
    evm_erc20_asset_claim,
    evm_native_asset_claim,
    near_native_asset_claim,
    resolve_instrument_identity,
)


def test_resolve_instrument_identity_normalizes_symbol_venue_and_value() -> None:
    result = resolve_instrument_identity(
        (
            InstrumentIdentityClaim(
                scheme="symbol",
                value="btc",
                venue="CoinBase",
                kind_hint=InstrumentKind.CRYPTO,
                display_name="Bitcoin",
            ),
            InstrumentIdentityClaim(
                scheme="symbol",
                value=" BTC ",
                venue="coinbase",
                kind_hint=InstrumentKind.CRYPTO,
                display_name="",
            ),
        )
    )

    assert result is not None
    assert str(result.instrument.instrument_id) == "symbol:BTC@coinbase"
    assert result.instrument.kind is InstrumentKind.CRYPTO
    assert result.instrument.display_name == "Bitcoin"
    assert [str(identifier.instrument_id) for identifier in result.identifiers] == [
        "symbol:BTC@coinbase",
        "symbol:BTC@coinbase",
    ]


def test_resolve_instrument_identity_rejects_conflicting_scheme_or_value() -> None:
    assert (
        resolve_instrument_identity(
            (
                InstrumentIdentityClaim(
                    scheme="symbol",
                    value="btc",
                    kind_hint=InstrumentKind.CRYPTO,
                ),
                InstrumentIdentityClaim(
                    scheme="symbol",
                    value="eth",
                    kind_hint=InstrumentKind.CRYPTO,
                ),
            )
        )
        is None
    )
    assert (
        resolve_instrument_identity(
            (
                InstrumentIdentityClaim(
                    scheme="symbol",
                    value="btc",
                    kind_hint=InstrumentKind.CRYPTO,
                ),
                InstrumentIdentityClaim(
                    scheme="asset",
                    value="evm:ethereum:native",
                    kind_hint=InstrumentKind.CRYPTO,
                ),
            )
        )
        is None
    )


def test_resolve_instrument_identity_rejects_conflicting_precision_hints() -> None:
    assert (
        resolve_instrument_identity(
            (
                InstrumentIdentityClaim(
                    scheme="symbol",
                    value="btc",
                    kind_hint=InstrumentKind.CRYPTO,
                    precision_hint=8,
                ),
                InstrumentIdentityClaim(
                    scheme="symbol",
                    value="btc",
                    kind_hint=InstrumentKind.CRYPTO,
                    precision_hint=6,
                ),
            )
        )
        is None
    )


def test_asset_claim_builders_emit_exact_values() -> None:
    assert asset_claim("evm:ethereum:native", display_name="Ethereum").scheme == "asset"
    assert asset_claim("evm:ethereum:native", display_name="Ethereum").value == (
        "evm:ethereum:native"
    )
    assert (
        asset_claim("evm:ethereum:native", display_name="Ethereum").kind_hint
        is InstrumentKind.CRYPTO
    )
    assert evm_native_asset_claim("Ethereum").value == "evm:ethereum:native"
    assert evm_native_asset_claim("Ethereum").display_name == "ETHEREUM"
    assert evm_native_asset_claim("Ethereum").kind_hint is InstrumentKind.CRYPTO
    assert evm_erc20_asset_claim("Arbitrum", "0xABC").value == (
        "evm:arbitrum:erc20:0xabc"
    )
    assert evm_erc20_asset_claim("Arbitrum", "0xABC").display_name == "0xabc"
    assert evm_erc20_asset_claim("Arbitrum", "0xABC").kind_hint is InstrumentKind.CRYPTO
    assert near_native_asset_claim().value == "near:native"
    assert near_native_asset_claim().display_name == "NEAR"
    assert near_native_asset_claim().kind_hint is InstrumentKind.CRYPTO
