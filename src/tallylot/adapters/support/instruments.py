"""Shared instrument identity resolution helpers for adapters."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.instruments import (
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
