"""Shared instrument identity resolution helpers for adapters."""

from __future__ import annotations

from tallylot.domain.instruments import (
    InstrumentIdentityClaim,
    ResolvedInstrument,
    asset_claim as _asset_claim,
    evm_erc20_asset_claim as _evm_erc20_asset_claim,
    evm_native_asset_claim as _evm_native_asset_claim,
    near_native_asset_claim as _near_native_asset_claim,
    resolve_instrument_identity as _resolve_instrument_identity,
)

__all__ = [
    "ResolvedInstrument",
    "asset_claim",
    "evm_erc20_asset_claim",
    "evm_native_asset_claim",
    "near_native_asset_claim",
    "resolve_instrument_identity",
]


def asset_claim(
    asset_path: str,
    *,
    display_name: str,
    precision_hint: int | None = None,
) -> InstrumentIdentityClaim:
    return _asset_claim(
        asset_path,
        display_name=display_name,
        precision_hint=precision_hint,
    )


def evm_native_asset_claim(
    network: str,
    *,
    display_name: str = "",
    precision_hint: int | None = None,
) -> InstrumentIdentityClaim:
    return _evm_native_asset_claim(
        network,
        display_name=display_name,
        precision_hint=precision_hint,
    )


def evm_erc20_asset_claim(
    network: str,
    contract_address: str,
    *,
    display_name: str = "",
    precision_hint: int | None = None,
) -> InstrumentIdentityClaim:
    return _evm_erc20_asset_claim(
        network,
        contract_address,
        display_name=display_name,
        precision_hint=precision_hint,
    )


def near_native_asset_claim(
    *,
    display_name: str = "NEAR",
    precision_hint: int | None = None,
) -> InstrumentIdentityClaim:
    return _near_native_asset_claim(
        display_name=display_name,
        precision_hint=precision_hint,
    )


def resolve_instrument_identity(
    claims: tuple[InstrumentIdentityClaim, ...],
) -> ResolvedInstrument | None:
    return _resolve_instrument_identity(claims)
