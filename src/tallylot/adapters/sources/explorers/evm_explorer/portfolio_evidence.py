"""MetaMask portfolio evidence extraction for EVM explorer sources."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.families import (
    classified_csv_paths,
)
from tallylot.adapters.support import (
    IssueSpec,
    ReviewSpec,
    issue_record,
    read_csv_rows,
    resolve_instrument_identity,
    review_record,
)
from tallylot.adapters.support.drafts import symbol_claim
from tallylot.domain.instruments import InstrumentKind
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.source_profiles import SourceProfile

CHAIN_SCOPE_BY_LABEL = {
    "ARB": "arbitrum",
    "BSC": "bsc",
    "ETH": "ethereum",
    "POL": "polygon",
}
TOKEN_SYMBOL_PATTERN = re.compile(r"\((?P<symbol>[^()]+)\)\s*$")
CAPTURE_MONTH_PATTERN = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})$")


def extract_portfolio_balance_evidence(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    location_inventory: tuple[LocationInventoryRecord, ...],
    network_scope: str,
) -> tuple[
    tuple[BalanceEvidence, ...],
    tuple[IssueRecord, ...],
    tuple[NormalizationReviewRecord, ...],
]:
    portfolio_paths = tuple(
        path
        for path, family_id in classified_csv_paths(raw_dir)
        if family_id == "portfolio_balances"
    )
    if not portfolio_paths:
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
                        scope="balance_evidence",
                        kind="portfolio_location_unresolved",
                        message=(
                            "MetaMask portfolio rows were not admitted because the source folder "
                            "did not resolve to exactly one canonical location."
                        ),
                        raw_file=",".join(path.name for path in portfolio_paths),
                    )
                ),
            ),
        )
    as_of_at = _capture_month_as_of(raw_dir)
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
                        scope="balance_evidence",
                        kind="portfolio_as_of_unresolved",
                        message=(
                            "MetaMask portfolio rows were not admitted because the source folder "
                            "capture month could not be resolved to a deterministic as-of date."
                        ),
                        raw_file=",".join(path.name for path in portfolio_paths),
                    )
                ),
            ),
        )
    evidence: list[BalanceEvidence] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    location = location_inventory[0]
    for path in portfolio_paths:
        for row_index, row in enumerate(read_csv_rows(path), start=2):
            chain_label = (row.get("Chain") or "").strip().upper()
            row_scope = CHAIN_SCOPE_BY_LABEL.get(chain_label, "")
            if row_scope != network_scope:
                probable_destination = row_scope or "unknown"
                reviews.append(
                    review_record(
                        ReviewSpec(
                            review_id=f"{profile.source}:{path.name}:row:{row_index}:portfolio_row_not_admitted",
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            scope="balance_evidence",
                            kind="portfolio_row_not_admitted",
                            message=(
                                "MetaMask portfolio row was not admitted automatically because its chain "
                                "does not match this source folder; probable destination chain is "
                                f"{probable_destination}. "
                                "This remains advisory because other wallets or undiscovered captures may exist."
                            ),
                            raw_file=path.name,
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
                            issue_id=f"{profile.source}:{path.name}:row:{row_index}:invalid_portfolio_row",
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            severity="medium",
                            kind="invalid_portfolio_row",
                            message=(
                                "MetaMask portfolio row did not include a valid "
                                "same-chain quantity and token symbol."
                            ),
                            raw_file=path.name,
                            raw_row_ref=f"row:{row_index}",
                        )
                    )
                )
                continue
            resolved = resolve_instrument_identity(
                (
                    symbol_claim(
                        symbol,
                        venue="evm_explorer",
                        kind_hint=InstrumentKind.CRYPTO,
                    ),
                )
            )
            if resolved is None:
                issues.append(
                    issue_record(
                        IssueSpec(
                            issue_id=f"{profile.source}:{path.name}:row:{row_index}:instrument_identity_blocked",
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            severity="high",
                            kind="instrument_identity_blocked",
                            message=f"MetaMask portfolio row could not resolve token symbol {symbol}.",
                            raw_file=path.name,
                            raw_row_ref=f"row:{row_index}",
                        )
                    )
                )
                reviews.append(
                    review_record(
                        ReviewSpec(
                            review_id=f"{profile.source}:{path.name}:row:{row_index}:instrument_identity_review",
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            scope="balance_evidence",
                            kind="instrument_identity_review",
                            message=f"Review required for MetaMask portfolio token symbol {symbol}.",
                            raw_file=path.name,
                            raw_row_ref=f"row:{row_index}",
                            field_name="Token",
                            original_value=row.get("Token") or "",
                        )
                    )
                )
                continue
            evidence.append(
                BalanceEvidence(
                    source=profile.source,
                    location_id=location.location_id,
                    instrument_id=resolved.instrument.instrument_id,
                    quantity=amount,
                    as_of_at=as_of_at,
                    as_of_precision=TemporalPrecision.DATE,
                    evidence_ref=f"{path.name}#row:{row_index}",
                    notes=(
                        "MetaMask portfolio quantity admitted for the source folder chain only; "
                        "wallet identity remains source-folder-scoped evidence."
                    ),
                )
            )
    return tuple(evidence), tuple(issues), tuple(reviews)


def _capture_month_as_of(raw_dir: Path) -> datetime | None:
    match = CAPTURE_MONTH_PATTERN.fullmatch(raw_dir.name)
    if match is None:
        return None
    return datetime(
        int(match.group("year")),
        int(match.group("month")),
        1,
        tzinfo=UTC,
    )


def _extract_symbol(value: str) -> str:
    match = TOKEN_SYMBOL_PATTERN.search(value.strip())
    if match is not None:
        return match.group("symbol").strip().upper()
    return value.strip().upper()
