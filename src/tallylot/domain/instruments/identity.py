"""Instrument identity resolution and reusable asset claims."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    InstrumentId,
    InstrumentIdentifierRecord,
    InstrumentIdentityClaim,
    InstrumentKind,
    InstrumentRecord,
)


@dataclass(frozen=True)
class ResolvedInstrument:
    instrument: InstrumentRecord
    identifiers: tuple[InstrumentIdentifierRecord, ...]


def asset_claim(
    asset_path: str,
    *,
    display_name: str,
    precision_hint: int | None = None,
) -> InstrumentIdentityClaim:
    normalized_path = asset_path.strip().lower()
    if not normalized_path:
        raise ValueError("asset claim path must not be blank")
    return InstrumentIdentityClaim(
        scheme="asset",
        value=normalized_path,
        kind_hint=InstrumentKind.CRYPTO,
        display_name=display_name.strip(),
        precision_hint=precision_hint,
    )


def evm_native_asset_claim(
    network: str,
    *,
    display_name: str = "",
    precision_hint: int | None = None,
) -> InstrumentIdentityClaim:
    normalized_network = network.strip().lower()
    if not normalized_network:
        raise ValueError("evm native asset claim network must not be blank")
    return asset_claim(
        f"evm:{normalized_network}:native",
        display_name=display_name or normalized_network.upper(),
        precision_hint=precision_hint,
    )


def evm_erc20_asset_claim(
    network: str,
    contract_address: str,
    *,
    display_name: str = "",
    precision_hint: int | None = None,
) -> InstrumentIdentityClaim:
    normalized_network = network.strip().lower()
    normalized_contract = contract_address.strip().lower()
    if not normalized_network:
        raise ValueError("evm erc20 asset claim network must not be blank")
    if not normalized_contract:
        raise ValueError("evm erc20 asset claim contract_address must not be blank")
    return asset_claim(
        f"evm:{normalized_network}:erc20:{normalized_contract}",
        display_name=display_name or normalized_contract,
        precision_hint=precision_hint,
    )


def near_native_asset_claim(
    *,
    display_name: str = "NEAR",
    precision_hint: int | None = None,
) -> InstrumentIdentityClaim:
    return asset_claim(
        "near:native",
        display_name=display_name,
        precision_hint=precision_hint,
    )


def resolve_instrument_identity(
    claims: tuple[InstrumentIdentityClaim, ...],
) -> ResolvedInstrument | None:
    normalized_claims = tuple(_normalize_claim(claim) for claim in claims)
    unique_keys = {_claim_key(claim) for claim in normalized_claims}
    if len(unique_keys) != 1:
        return None
    kinds = {
        claim.kind_hint
        for claim in normalized_claims
        if claim.kind_hint is not InstrumentKind.UNKNOWN
    }
    if len(kinds) > 1:
        return None
    precisions = {
        claim.precision_hint
        for claim in normalized_claims
        if claim.precision_hint is not None
    }
    if len(precisions) > 1:
        return None
    representative = normalized_claims[0]
    instrument_id = InstrumentId(_instrument_id_text(representative))
    display_name = next(
        (claim.display_name for claim in normalized_claims if claim.display_name),
        representative.value,
    )
    return ResolvedInstrument(
        instrument=InstrumentRecord(
            instrument_id=instrument_id,
            kind=next(iter(kinds), InstrumentKind.UNKNOWN),
            display_name=display_name,
            precision=next(iter(precisions), None),
        ),
        identifiers=tuple(
            InstrumentIdentifierRecord(
                instrument_id=instrument_id,
                scheme=claim.scheme,
                value=claim.value,
                venue=claim.venue,
            )
            for claim in normalized_claims
        ),
    )


def _normalize_claim(claim: InstrumentIdentityClaim) -> InstrumentIdentityClaim:
    normalized_value = claim.value.strip()
    if claim.scheme == "symbol":
        normalized_value = normalized_value.upper()
    normalized_venue = (
        None
        if claim.venue is None or not claim.venue.strip()
        else claim.venue.strip().lower()
    )
    return InstrumentIdentityClaim(
        scheme=claim.scheme.strip(),
        value=normalized_value,
        venue=normalized_venue,
        kind_hint=claim.kind_hint,
        display_name=claim.display_name.strip(),
        precision_hint=claim.precision_hint,
    )


def _claim_key(claim: InstrumentIdentityClaim) -> tuple[str, str, str]:
    return claim.scheme, claim.value, "" if claim.venue is None else claim.venue


def _instrument_id_text(claim: InstrumentIdentityClaim) -> str:
    venue_suffix = "" if claim.venue is None else f"@{claim.venue}"
    return f"{claim.scheme}:{claim.value}{venue_suffix}"
