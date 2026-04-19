"""Source-backed statement balance evidence extraction."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, cast

from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceTarget,
)
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.instruments.identity import resolve_instrument_identity
from tallylot.domain.location_identifiers import location_id_from_parts
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId
from tallylot.ports.evidence import (
    StatementBalanceReferenceBatch,
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile

from .collection import collect_source_statement_documents_from_inventory
from .collection import document_precedence_value as _document_precedence_value
from .collection import document_provenance as _document_provenance
from .hooks import StatementDocumentEvidenceAdapter
from .issues import instrument_issue, instrument_review, missing_quantity_issue
from .models import StatementDocumentCollectionResult


def extract_source_balance_references_from_inventory(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    raw_dir: Path,
    *,
    extract_pdf_text: Callable[[Path], str],
) -> StatementBalanceReferenceBatch:
    collection = collect_source_statement_documents_from_inventory(
        adapter,
        profile,
        raw_dir,
        extract_pdf_text=extract_pdf_text,
    )
    return extract_source_balance_references_from_collection(
        adapter,
        profile,
        collection,
    )


def extract_source_balance_references_from_collection(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    collection: StatementDocumentCollectionResult,
) -> StatementBalanceReferenceBatch:
    selected_documents = tuple(
        sorted(
            (
                (document.entry, document.parsed)
                for document in collection.collected_documents
                if document.selected
            ),
            key=lambda item: (
                _document_precedence_value(item[1]),
                item[0].relative_path,
            ),
            reverse=True,
        )
    )
    if not selected_documents:
        return StatementBalanceReferenceBatch(
            balance_references=(),
            reference_issues=(),
            issues=collection.issues,
            reviews=collection.reviews,
        )
    references = _balance_references_from_statement_documents(
        adapter,
        profile,
        selected_documents,
        issues=list(collection.issues),
        reviews=list(collection.reviews),
    )
    return StatementBalanceReferenceBatch(
        balance_references=references,
        reference_issues=(),
        issues=collection.issues,
        reviews=collection.reviews,
    )


def _balance_references_from_statement_documents(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    documents: tuple[tuple[object, object], ...],
    *,
    issues: list[IssueRecord],
    reviews: list[NormalizationReviewRecord],
) -> tuple[BalanceReference, ...]:
    seen_rows: set[tuple[object, ...]] = set()
    aggregated: dict[
        tuple[str, str, str, datetime, TemporalPrecision, str],
        tuple[Decimal, set[str], set[str], InstrumentId, ProvenanceLocator],
    ] = {}
    for entry_value, parsed_value in documents:
        entry = cast(FileInventoryEntry, entry_value)
        parsed = cast(StatementDocumentParseResult, parsed_value)
        for row in parsed.rows:
            row_location_id = _statement_row_location_id(profile, row)
            row_key = _statement_row_precedence_key(row)
            if row_key in seen_rows:
                continue
            seen_rows.add(row_key)
            provenance = _document_provenance(entry, anchor=row.raw_row_ref)
            if row.quantity is None or row.as_of_at is None:
                issues.append(
                    missing_quantity_issue(adapter, profile, entry, provenance, row)
                )
                continue
            resolved = resolve_instrument_identity(
                adapter.resolve_statement_instrument_claims(row)
            )
            if resolved is None:
                issues.append(
                    instrument_issue(adapter, profile, entry, provenance, row)
                )
                reviews.append(
                    instrument_review(adapter, profile, entry, provenance, row)
                )
                continue
            provenance_key = replace(provenance, anchor="").to_reference_ref()
            key = (
                str(row_location_id),
                str(resolved.instrument.instrument_id),
                row.balance_kind,
                row.as_of_at,
                row.as_of_precision,
                provenance_key,
            )
            quantity, anchors, notes, instrument_id, row_provenance = aggregated.get(
                key,
                (
                    Decimal("0"),
                    set(),
                    set(),
                    resolved.instrument.instrument_id,
                    provenance,
                ),
            )
            if row.raw_row_ref:
                anchors.add(row.raw_row_ref)
            if row.notes:
                notes.add(row.notes)
            aggregated[key] = (
                quantity + row.quantity,
                anchors,
                notes,
                instrument_id,
                row_provenance,
            )
    return _references_from_aggregated_rows(profile, aggregated)


def _statement_row_precedence_key(
    row: StatementDocumentBalanceRow,
) -> tuple[object, ...]:
    return (
        row.account,
        row.wallet,
        row.balance_kind,
        row.asset,
        row.as_of_at,
        row.as_of_precision,
        row.as_of_text,
    )


def _statement_row_location_id(
    profile: SourceProfile,
    row: StatementDocumentBalanceRow,
) -> LocationId:
    wallet_segment = row.wallet.strip()
    account_segment = row.account.strip()
    if wallet_segment and not _matches_source_label(profile, wallet_segment):
        return location_id_from_parts(str(profile.source), wallet_segment)
    if account_segment and not _matches_source_label(profile, account_segment):
        return location_id_from_parts(str(profile.source), account_segment)
    return location_id_from_parts(str(profile.source))


def _matches_source_label(profile: SourceProfile, segment: str) -> bool:
    return segment.strip().casefold() == str(profile.source).strip().casefold()


def _references_from_aggregated_rows(
    profile: SourceProfile,
    aggregated: dict[
        tuple[str, str, str, datetime, TemporalPrecision, str],
        tuple[Decimal, set[str], set[str], InstrumentId, ProvenanceLocator],
    ],
) -> tuple[BalanceReference, ...]:
    references: list[BalanceReference] = []
    for (
        location_id,
        _instrument_key,
        balance_kind,
        as_of_at,
        as_of_precision,
        _provenance_ref,
    ), (
        quantity,
        anchors,
        notes,
        instrument_id,
        provenance,
    ) in sorted(aggregated.items()):
        references.append(
            BalanceReference(
                target=BalanceTarget(
                    source=profile.source,
                    location_id=LocationId(location_id),
                    instrument_id=instrument_id,
                    balance_kind=_reference_balance_kind(balance_kind),
                    target_at=as_of_at,
                    target_precision=as_of_precision,
                ),
                quantity=quantity,
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=as_of_at,
                observed_precision=as_of_precision,
                support_ref=replace(
                    provenance,
                    anchor=" + ".join(sorted(anchors)) or provenance.anchor,
                ).to_reference_ref(),
                notes=" | ".join(sorted(notes)),
            )
        )
    return tuple(references)


def _reference_balance_kind(balance_kind: str) -> str:
    normalized = balance_kind.strip()
    if normalized in {"asset_balance", "cash_closing_balance"}:
        return "available"
    return normalized
