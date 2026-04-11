"""MetaMask portfolio evidence extraction for EVM explorer sources."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.families import (
    family_id_for_header,
)
from tallylot.adapters.support import (
    IssueSpec,
    ReviewSpec,
    evm_native_asset_claim,
    issue_record,
    read_csv_rows,
    resolve_instrument_identity,
    review_record,
)
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceTarget,
)
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.instruments import InstrumentIdentityClaim
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.source_profiles import (
    FileInventoryEntry,
    SourceProfile,
    parse_family_claim_tokens,
)

CHAIN_SCOPE_BY_LABEL = {
    "ARB": "arbitrum",
    "BSC": "bsc",
    "ETH": "ethereum",
    "POL": "polygon",
}
CHAIN_NATIVE_SYMBOL_BY_SCOPE = {
    "arbitrum": "ETH",
    "bsc": "BNB",
    "ethereum": "ETH",
    "polygon": "POL",
}
TOKEN_SYMBOL_PATTERN = re.compile(r"\((?P<symbol>[^()]+)\)\s*$")


def extract_portfolio_balance_references(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    location_inventory: tuple[LocationInventoryRecord, ...],
    network_scope: str,
) -> tuple[
    tuple[BalanceReference, ...],
    tuple[IssueRecord, ...],
    tuple[NormalizationReviewRecord, ...],
]:
    portfolio_entries = _portfolio_entries(profile, raw_dir)
    if not portfolio_entries:
        return (), (), ()
    if len(location_inventory) != 1:
        return (
            (),
            (),
            (
                review_record(
                    ReviewSpec(
                        review_id=f"{profile.source}:portfolio_location_unresolved",
                        source=str(profile.source),
                        adapter_id="evm_explorer",
                        scope="balance_reference",
                        kind="portfolio_location_unresolved",
                        message=(
                            "MetaMask portfolio rows were not admitted because the source folder "
                            "did not resolve to exactly one location."
                        ),
                        raw_file=",".join(
                            entry.relative_path for entry, _ in portfolio_entries
                        ),
                    )
                ),
            ),
        )
    as_of_at = _portfolio_as_of(profile, portfolio_entries)
    if as_of_at is None:
        return (
            (),
            (),
            (
                review_record(
                    ReviewSpec(
                        review_id=f"{profile.source}:portfolio_as_of_unresolved",
                        source=str(profile.source),
                        adapter_id="evm_explorer",
                        scope="balance_reference",
                        kind="portfolio_as_of_unresolved",
                        message=(
                            "MetaMask portfolio rows were not admitted because no deterministic "
                            "as-of date could be resolved from typed profile metadata."
                        ),
                        raw_file=",".join(
                            entry.relative_path for entry, _ in portfolio_entries
                        ),
                    )
                ),
            ),
        )
    references: list[BalanceReference] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    location = location_inventory[0]
    for entry, path in portfolio_entries:
        for row_index, row in enumerate(read_csv_rows(path), start=2):
            chain_label = (row.get("Chain") or "").strip().upper()
            row_scope = CHAIN_SCOPE_BY_LABEL.get(chain_label, "")
            if row_scope != network_scope:
                probable_destination = row_scope or "unknown"
                reviews.append(
                    review_record(
                        ReviewSpec(
                            review_id=(
                                f"{profile.source}:{entry.relative_path}:row:{row_index}:"
                                "portfolio_row_not_admitted"
                            ),
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            scope="balance_reference",
                            kind="portfolio_row_not_admitted",
                            message=(
                                "MetaMask portfolio row was not admitted automatically because its chain "
                                "does not match this source folder; probable destination chain is "
                                f"{probable_destination}. "
                                "This remains advisory because other wallets or undiscovered captures may exist."
                            ),
                            raw_file=entry.relative_path,
                            raw_row_ref=f"row:{row_index}",
                            field_name="Chain",
                            original_value=chain_label,
                        )
                    )
                )
                continue
            amount = parse_decimal((row.get("Amount") or "").replace(",", "").strip())
            symbol = _extract_symbol(row.get("Token") or "")
            if amount is None or amount <= Decimal("0") or not symbol:
                issues.append(
                    issue_record(
                        IssueSpec(
                            issue_id=f"{profile.source}:{entry.relative_path}:row:{row_index}:invalid_portfolio_row",
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            severity="medium",
                            kind="invalid_portfolio_row",
                            message=(
                                "MetaMask portfolio row did not include a valid "
                                "same-chain quantity and token symbol."
                            ),
                            raw_file=entry.relative_path,
                            raw_row_ref=f"row:{row_index}",
                        )
                    )
                )
                continue
            try:
                asset_claim = _portfolio_asset_claim(row_scope, symbol)
            except ValueError:
                asset_claim = None
            resolved = (
                None
                if asset_claim is None
                else resolve_instrument_identity((asset_claim,))
            )
            if resolved is None:
                issues.append(
                    issue_record(
                        IssueSpec(
                            issue_id=(
                                f"{profile.source}:{entry.relative_path}:row:"
                                f"{row_index}:instrument_identity_blocked"
                            ),
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            severity="high",
                            kind="instrument_identity_blocked",
                            message=(
                                "MetaMask portfolio row could not resolve an "
                                "immutable on-chain asset id "
                                f"for token symbol {symbol}."
                            ),
                            raw_file=entry.relative_path,
                            raw_row_ref=f"row:{row_index}",
                        )
                    )
                )
                reviews.append(
                    review_record(
                        ReviewSpec(
                            review_id=(
                                f"{profile.source}:{entry.relative_path}:row:{row_index}:"
                                "instrument_identity_review"
                            ),
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            scope="balance_reference",
                            kind="instrument_identity_review",
                            message=(
                                "Review required because the portfolio export did not prove an immutable "
                                f"on-chain asset id for token symbol {symbol}."
                            ),
                            raw_file=entry.relative_path,
                            raw_row_ref=f"row:{row_index}",
                            field_name="Token",
                            original_value=row.get("Token") or "",
                        )
                    )
                )
                continue
            references.append(
                BalanceReference(
                    target=BalanceTarget(
                        source=profile.source,
                        location_id=location.location_id,
                        instrument_id=resolved.instrument.instrument_id,
                        balance_kind="available",
                        target_at=as_of_at,
                        target_precision=TemporalPrecision.DATE,
                    ),
                    quantity=amount,
                    reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                    observed_at=as_of_at,
                    observed_precision=TemporalPrecision.DATE,
                    support_ref=ProvenanceLocator.from_reference_ref(
                        f"{entry.relative_path}#row:{row_index}"
                    ).to_reference_ref(),
                    notes=(
                        "MetaMask portfolio quantity admitted for the source folder chain only; "
                        "wallet identity remains source-folder-scoped evidence."
                    ),
                )
            )
    return tuple(references), tuple(issues), tuple(reviews)


def _portfolio_asset_claim(
    row_scope: str,
    symbol: str,
) -> InstrumentIdentityClaim:
    native_symbol = CHAIN_NATIVE_SYMBOL_BY_SCOPE.get(row_scope, "")
    if native_symbol and symbol == native_symbol:
        return evm_native_asset_claim(row_scope, display_name=symbol)
    raise ValueError(
        "portfolio token rows without immutable contract identity cannot be canonicalized"
    )


def _portfolio_entries(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[tuple[FileInventoryEntry, Path], ...]:
    entries: list[tuple[FileInventoryEntry, Path]] = []
    for entry in profile.file_inventory:
        if entry.suffix.lower() != ".csv":
            continue
        if not _is_portfolio_entry(entry):
            continue
        path = _inventory_path(raw_dir, entry)
        if path is None:
            continue
        entries.append((entry, path))
    return tuple(sorted(entries, key=lambda item: item[0].relative_path))


def _is_portfolio_entry(entry: FileInventoryEntry) -> bool:
    family_ids = {
        family_id
        for adapter_id, family_id in parse_family_claim_tokens(entry.family)
        if adapter_id == "evm_explorer"
    }
    if "portfolio_balances" in family_ids:
        return True
    return family_id_for_header(entry.header) == "portfolio_balances"


def _inventory_path(raw_dir: Path, entry: FileInventoryEntry) -> Path | None:
    candidates: list[Path] = []
    if entry.source_path:
        candidates.append(Path(entry.source_path))
    candidates.append(raw_dir / entry.relative_path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _portfolio_as_of(
    profile: SourceProfile,
    portfolio_entries: tuple[tuple[FileInventoryEntry, Path], ...],
) -> datetime | None:
    report_period_end = max(
        (
            parsed
            for entry, _ in portfolio_entries
            if (parsed := _parse_inventory_date(entry.report_period_end)) is not None
        ),
        default=None,
    )
    if report_period_end is not None:
        return report_period_end
    observed_period_end = max(
        (
            parsed
            for entry, _ in portfolio_entries
            if (parsed := _parse_inventory_date(entry.observed_period_end)) is not None
        ),
        default=None,
    )
    if observed_period_end is not None:
        return observed_period_end
    latest_timestamp = max(
        (
            parsed
            for entry in profile.file_inventory
            if (parsed := _parse_inventory_timestamp(entry.max_timestamp)) is not None
        ),
        default=None,
    )
    if latest_timestamp is None:
        return None
    return latest_timestamp.astimezone(UTC).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def _parse_inventory_date(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    try:
        parsed = parse_temporal_value(text, precision=TemporalPrecision.DATE)
    except ValueError:
        try:
            parsed = parse_temporal_value(text, precision=TemporalPrecision.TIMESTAMP)
        except ValueError:
            return None
    return parsed.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_inventory_timestamp(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    try:
        return parse_temporal_value(text, precision=TemporalPrecision.TIMESTAMP)
    except ValueError:
        return None


def _extract_symbol(value: str) -> str:
    match = TOKEN_SYMBOL_PATTERN.search(value.strip())
    if match is not None:
        return match.group("symbol").strip().upper()
    return value.strip().upper()
