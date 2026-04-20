"""Shared statement extraction result models."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.evidence import EvidenceMemberStatus
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.ports.evidence import StatementDocumentParseResult
from tallylot.ports.source_profiles import FileInventoryEntry


@dataclass(frozen=True)
class PdfBalanceRows:
    adapter_id: str
    rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class CollectedStatementDocument:
    entry: FileInventoryEntry
    parsed: StatementDocumentParseResult
    locator: tuple[str, str]
    member_status: EvidenceMemberStatus
    selected: bool
    statement_as_of_precision: TemporalPrecision | None
    document_effective_precision: TemporalPrecision | None


@dataclass(frozen=True)
class StatementDocumentCollectionResult:
    collected_documents: tuple[CollectedStatementDocument, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
