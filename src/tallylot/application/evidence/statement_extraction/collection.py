"""Statement document collection helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.evidence import EvidenceMemberStatus
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import CaptureUid
from tallylot.ports.evidence import StatementDocumentParseResult
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile

from .hooks import StatementDocumentEvidenceAdapter
from .issues import (
    StatementIssueDetails,
    ambiguous_statement_issue,
    statement_issue,
)
from .models import CollectedStatementDocument, StatementDocumentCollectionResult


def collect_source_statement_documents_from_inventory(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    raw_dir: Path,
    *,
    extract_pdf_text: Callable[[Path], str],
) -> StatementDocumentCollectionResult:
    candidates = tuple(statement_document_candidates(profile, raw_dir))
    if not candidates:
        return StatementDocumentCollectionResult(
            collected_documents=(),
            issues=(),
            reviews=(),
        )
    recognized: list[tuple[FileInventoryEntry, StatementDocumentParseResult]] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    for entry, pdf_path in candidates:
        provenance = document_provenance(entry)
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
    latest_documents = latest_recognized_documents(recognized)
    latest_paths = {entry.relative_path for entry, _ in latest_documents}
    collected: list[CollectedStatementDocument] = []
    if not latest_documents:
        append_missing_as_of_issue(adapter, profile, recognized, issues)
        for entry, parsed in recognized:
            collected.append(
                CollectedStatementDocument(
                    entry=entry,
                    parsed=parsed,
                    locator=(entry.relative_path, entry.archive_member_path or ""),
                    member_status=EvidenceMemberStatus.BLOCKED,
                    selected=False,
                    statement_as_of_precision=statement_as_of_precision(parsed),
                    document_effective_precision=document_effective_precision(parsed),
                )
            )
        return StatementDocumentCollectionResult(
            collected_documents=tuple(
                sorted(collected, key=lambda item: item.entry.relative_path)
            ),
            issues=tuple(issues),
            reviews=tuple(reviews),
        )
    if len(latest_documents) > 1:
        append_ambiguous_statement_issues(adapter, profile, latest_documents, issues)
        for entry, parsed in recognized:
            collected.append(
                CollectedStatementDocument(
                    entry=entry,
                    parsed=parsed,
                    locator=(entry.relative_path, entry.archive_member_path or ""),
                    member_status=(
                        EvidenceMemberStatus.BLOCKED
                        if entry.relative_path in latest_paths
                        else EvidenceMemberStatus.SUPERSEDED
                    ),
                    selected=False,
                    statement_as_of_precision=statement_as_of_precision(parsed),
                    document_effective_precision=document_effective_precision(parsed),
                )
            )
        return StatementDocumentCollectionResult(
            collected_documents=tuple(
                sorted(collected, key=lambda item: item.entry.relative_path)
            ),
            issues=tuple(issues),
            reviews=tuple(reviews),
        )
    selected_documents = evidence_documents_for_latest_snapshot(
        recognized, latest_documents
    )
    selected_paths = {entry.relative_path for entry, _ in selected_documents}
    for entry, parsed in recognized:
        collected.append(
            CollectedStatementDocument(
                entry=entry,
                parsed=parsed,
                locator=(entry.relative_path, entry.archive_member_path or ""),
                member_status=(
                    EvidenceMemberStatus.SELECTED
                    if entry.relative_path in selected_paths
                    else EvidenceMemberStatus.SUPERSEDED
                ),
                selected=entry.relative_path in selected_paths,
                statement_as_of_precision=statement_as_of_precision(parsed),
                document_effective_precision=document_effective_precision(parsed),
            )
        )
    return StatementDocumentCollectionResult(
        collected_documents=tuple(
            sorted(collected, key=lambda item: item.entry.relative_path)
        ),
        issues=tuple(issues),
        reviews=tuple(reviews),
    )


def statement_document_candidates(
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
        path = inventory_path(raw_dir, entry)
        if path is None:
            continue
        candidates.append((entry, path))
    return tuple(sorted(candidates, key=lambda item: item[0].relative_path))


def inventory_path(raw_dir: Path, entry: FileInventoryEntry) -> Path | None:
    candidates: list[Path] = []
    if entry.source_path:
        candidates.append(Path(entry.source_path))
    candidates.append(raw_dir / entry.relative_path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def document_provenance(
    entry: FileInventoryEntry, *, anchor: str = ""
) -> ProvenanceLocator:
    return ProvenanceLocator(
        capture_uid=CaptureUid(entry.capture_uid),
        relative_path=entry.archive_source_path or entry.relative_path,
        archive_member_path=entry.archive_member_path,
        locator_kind="raw_file",
        anchor=anchor,
    )


def latest_recognized_documents(
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


def append_missing_as_of_issue(
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
            document_provenance(entry),
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


def append_ambiguous_statement_issues(
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
                document_provenance(entry),
                matched_paths=matched_paths,
            )
        )


def evidence_documents_for_latest_snapshot(
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
                document_precedence_value(item[1]),
                item[0].relative_path,
            ),
            reverse=True,
        )
    )


def document_precedence_value(parsed: StatementDocumentParseResult) -> datetime:
    return (
        parsed.document_effective_at
        or parsed.statement_as_of_at
        or datetime.min.replace(tzinfo=UTC)
    )


def statement_as_of_precision(
    parsed: StatementDocumentParseResult,
) -> TemporalPrecision | None:
    precisions = {
        row.as_of_precision for row in parsed.rows if row.as_of_at is not None
    }
    if not precisions:
        return None
    if TemporalPrecision.TIMESTAMP in precisions:
        return TemporalPrecision.TIMESTAMP
    return TemporalPrecision.DATE


def document_effective_precision(
    parsed: StatementDocumentParseResult,
) -> TemporalPrecision | None:
    if parsed.document_effective_at is None:
        return None
    return TemporalPrecision.DATE
