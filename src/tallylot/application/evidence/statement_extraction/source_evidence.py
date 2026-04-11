"""Source-backed statement balance evidence extraction."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable

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
from tallylot.domain.types import CaptureUid, LocationId
from tallylot.ports.evidence import (
    StatementBalanceReferenceBatch,
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile

from .hooks import StatementDocumentEvidenceAdapter
from .issues import (
    StatementIssueDetails,
    ambiguous_statement_issue,
    instrument_issue,
    instrument_review,
    missing_quantity_issue,
    statement_issue,
)


def extract_source_balance_references_from_inventory(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    raw_dir: Path,
    *,
    extract_pdf_text: Callable[[Path], str],
) -> StatementBalanceReferenceBatch:
    candidates = tuple(_statement_document_candidates(profile, raw_dir))
    if not candidates:
        return StatementBalanceReferenceBatch(
            balance_references=(),
            reference_issues=(),
            issues=(),
            reviews=(),
        )
    recognized: list[tuple[FileInventoryEntry, StatementDocumentParseResult]] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    for entry, pdf_path in candidates:
        provenance = _document_provenance(entry)
        text = extract_pdf_text(pdf_path)
        if adapter.match_statement_document(pdf_path, text) <= 0:
            continue
        parsed = adapter.parse_statement_document(pdf_path, text)
        if not parsed.recognized:
            issues.append(
                statement_issue(
                    adapter,
                    profile,
                    entry,
                    provenance,
                    StatementIssueDetails(
                        kind="statement_document_unrecognized",
                        severity="medium",
                        message=(
                            f"{adapter.manifest.display_name} could not recognize "
                            f"statement document {entry.relative_path}."
                        ),
                    ),
                )
            )
            continue
        if not parsed.rows:
            issues.append(
                statement_issue(
                    adapter,
                    profile,
                    entry,
                    provenance,
                    StatementIssueDetails(
                        kind="statement_evidence_missing",
                        severity="high",
                        message=(
                            f"{adapter.manifest.display_name} statement document "
                            f"{entry.relative_path} was recognized but no balance "
                            "rows were extracted."
                        ),
                    ),
                )
            )
            continue
        recognized.append((entry, parsed))
    latest_documents = _latest_recognized_documents(recognized)
    if not latest_documents:
        _append_missing_as_of_issue(
            adapter,
            profile,
            recognized,
            issues,
        )
        return StatementBalanceReferenceBatch(
            balance_references=(),
            reference_issues=(),
            issues=tuple(issues),
            reviews=tuple(reviews),
        )
    if len(latest_documents) > 1:
        _append_ambiguous_statement_issues(
            adapter,
            profile,
            latest_documents,
            issues,
        )
        return StatementBalanceReferenceBatch(
            balance_references=(),
            reference_issues=(),
            issues=tuple(issues),
            reviews=tuple(reviews),
        )
    references = _balance_references_from_statement_documents(
        adapter,
        profile,
        _evidence_documents_for_latest_snapshot(recognized, latest_documents),
        issues=issues,
        reviews=reviews,
    )
    return StatementBalanceReferenceBatch(
        balance_references=references,
        reference_issues=(),
        issues=tuple(issues),
        reviews=tuple(reviews),
    )


def _statement_document_candidates(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[tuple[FileInventoryEntry, Path], ...]:
    candidates: list[tuple[FileInventoryEntry, Path]] = []
    for entry in profile.file_inventory:
        if entry.suffix.lower() != ".pdf":
            continue
        if entry.evidence_role and entry.evidence_role != "statement_source":
            continue
        if entry.statement_kind and entry.statement_kind != str(profile.adapter_id):
            continue
        if entry.originality_class and entry.originality_class != "upstream_original":
            continue
        path = _inventory_path(raw_dir, entry)
        if path is None:
            continue
        candidates.append((entry, path))
    return tuple(sorted(candidates, key=lambda item: item[0].relative_path))


def _inventory_path(raw_dir: Path, entry: FileInventoryEntry) -> Path | None:
    candidates: list[Path] = []
    if entry.source_path:
        candidates.append(Path(entry.source_path))
    candidates.append(raw_dir / entry.relative_path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _document_provenance(
    entry: FileInventoryEntry, *, anchor: str = ""
) -> ProvenanceLocator:
    return ProvenanceLocator(
        capture_uid=CaptureUid(entry.capture_uid),
        relative_path=entry.archive_source_path or entry.relative_path,
        archive_member_path=entry.archive_member_path,
        locator_kind="raw_file",
        anchor=anchor,
    )


def _latest_recognized_documents(
    documents: list[tuple[FileInventoryEntry, StatementDocumentParseResult]],
) -> tuple[tuple[FileInventoryEntry, StatementDocumentParseResult], ...]:
    effective_dated = tuple(
        (entry, parsed)
        for entry, parsed in documents
        if parsed.document_effective_at is not None
    )
    if effective_dated:
        latest_effective_at = max(
            parsed.document_effective_at
            for _, parsed in effective_dated
            if parsed.document_effective_at is not None
        )
        return tuple(
            (entry, parsed)
            for entry, parsed in effective_dated
            if parsed.document_effective_at == latest_effective_at
        )
    dated = tuple(
        (entry, parsed)
        for entry, parsed in documents
        if parsed.statement_as_of_at is not None
    )
    if not dated:
        return ()
    latest_as_of = max(
        parsed.statement_as_of_at
        for _, parsed in dated
        if parsed.statement_as_of_at is not None
    )
    return tuple(
        (entry, parsed)
        for entry, parsed in dated
        if parsed.statement_as_of_at == latest_as_of
    )


def _append_missing_as_of_issue(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    recognized: list[tuple[FileInventoryEntry, StatementDocumentParseResult]],
    issues: list[IssueRecord],
) -> None:
    if not recognized:
        return
    entry = recognized[0][0]
    issues.append(
        statement_issue(
            adapter,
            profile,
            entry,
            _document_provenance(entry),
            StatementIssueDetails(
                kind="statement_document_missing_as_of",
                severity="high",
                message=(
                    f"{adapter.manifest.display_name} statement document "
                    f"{entry.relative_path} was recognized but no statement date "
                    "could be determined."
                ),
            ),
        )
    )


def _append_ambiguous_statement_issues(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    latest_documents: tuple[
        tuple[FileInventoryEntry, StatementDocumentParseResult], ...
    ],
    issues: list[IssueRecord],
) -> None:
    matched_paths = tuple(entry.relative_path for entry, _ in latest_documents)
    for entry, _ in latest_documents:
        issues.append(
            ambiguous_statement_issue(
                adapter,
                profile,
                entry,
                _document_provenance(entry),
                matched_paths=matched_paths,
            )
        )


def _evidence_documents_for_latest_snapshot(
    recognized: list[tuple[FileInventoryEntry, StatementDocumentParseResult]],
    latest_documents: tuple[
        tuple[FileInventoryEntry, StatementDocumentParseResult], ...
    ],
) -> tuple[tuple[FileInventoryEntry, StatementDocumentParseResult], ...]:
    latest_statement_as_of = latest_documents[0][1].statement_as_of_at
    candidates = (
        latest_documents
        if latest_statement_as_of is None
        else tuple(
            (entry, parsed)
            for entry, parsed in recognized
            if parsed.statement_as_of_at == latest_statement_as_of
        )
    )
    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                _document_precedence_value(item[1]),
                item[0].relative_path,
            ),
            reverse=True,
        )
    )


def _balance_references_from_statement_documents(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    documents: tuple[tuple[FileInventoryEntry, StatementDocumentParseResult], ...],
    *,
    issues: list[IssueRecord],
    reviews: list[NormalizationReviewRecord],
) -> tuple[BalanceReference, ...]:
    seen_rows: set[tuple[object, ...]] = set()
    aggregated: dict[
        tuple[str, str, str, datetime, TemporalPrecision, str],
        tuple[Decimal, set[str], set[str], InstrumentId, ProvenanceLocator],
    ] = {}
    for entry, parsed in documents:
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


def _document_precedence_value(parsed: StatementDocumentParseResult) -> datetime:
    return (
        parsed.document_effective_at
        or parsed.statement_as_of_at
        or datetime.min.replace(tzinfo=UTC)
    )


def _statement_row_precedence_key(
    row: StatementDocumentBalanceRow,
) -> tuple[object, ...]:
    return (
        row.source,
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
    if wallet_segment:
        return location_id_from_parts(str(profile.source), wallet_segment)
    if account_segment:
        return location_id_from_parts(str(profile.source), account_segment)
    return location_id_from_parts(str(profile.source))


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
                    balance_kind=balance_kind,
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
