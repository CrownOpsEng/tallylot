"""Statement extraction issue and review record factories."""

from __future__ import annotations

from dataclasses import dataclass, replace

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.evidence import StatementDocumentBalanceRow
from tallylot.ports.source_profiles import FileInventoryEntry, SourceProfile

from .hooks import StatementDocumentEvidenceAdapter
from .rows import row_context_timestamp


@dataclass(frozen=True)
class StatementIssueDetails:
    kind: str
    severity: str
    message: str
    raw_row_ref: str = ""
    context_timestamp: str = ""


@dataclass(frozen=True)
class StatementReviewDetails:
    kind: str
    message: str
    raw_row_ref: str
    context_timestamp: str
    field_name: str
    original_value: str


def statement_issue(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    entry: FileInventoryEntry,
    provenance: ProvenanceLocator,
    details: StatementIssueDetails,
) -> IssueRecord:
    return IssueRecord(
        issue_id=f"{profile.source}:{entry.relative_path}:{details.kind}",
        source=str(profile.source),
        adapter_id=str(adapter.manifest.adapter_id),
        severity=details.severity,
        kind=details.kind,
        message=details.message,
        context_timestamp=details.context_timestamp,
        raw_file=entry.relative_path,
        raw_provenance=replace(provenance, anchor=""),
        raw_row_ref=details.raw_row_ref,
    )


def statement_review(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    entry: FileInventoryEntry,
    provenance: ProvenanceLocator,
    details: StatementReviewDetails,
) -> NormalizationReviewRecord:
    return NormalizationReviewRecord(
        review_id=f"{profile.source}:{entry.relative_path}:{details.raw_row_ref}:{details.kind}",
        source=str(profile.source),
        adapter_id=str(adapter.manifest.adapter_id),
        scope="balance_evidence",
        kind=details.kind,
        message=details.message,
        context_timestamp=details.context_timestamp,
        raw_file=entry.relative_path,
        raw_provenance=replace(provenance, anchor=""),
        raw_row_ref=details.raw_row_ref,
        field_name=details.field_name,
        original_value=details.original_value,
    )


def missing_quantity_issue(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    entry: FileInventoryEntry,
    provenance: ProvenanceLocator,
    row: StatementDocumentBalanceRow,
) -> IssueRecord:
    return statement_issue(
        adapter,
        profile,
        entry,
        provenance,
        StatementIssueDetails(
            kind="statement_evidence_missing",
            severity="high",
            message=(
                f"{adapter.manifest.display_name} statement row for "
                f"{row.asset or row.balance_kind} did not contain a quantity "
                "and timestamp."
            ),
            raw_row_ref=row.raw_row_ref,
            context_timestamp=row_context_timestamp(row),
        ),
    )


def ambiguous_statement_issue(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    entry: FileInventoryEntry,
    provenance: ProvenanceLocator,
    *,
    matched_paths: tuple[str, ...],
) -> IssueRecord:
    documents = ", ".join(matched_paths)
    return statement_issue(
        adapter,
        profile,
        entry,
        provenance,
        StatementIssueDetails(
            kind="statement_document_ambiguous",
            severity="high",
            message=(
                f"{adapter.manifest.display_name} matched multiple latest statement "
                f"documents for one capture: {documents}."
            ),
        ),
    )


def instrument_issue(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    entry: FileInventoryEntry,
    provenance: ProvenanceLocator,
    row: StatementDocumentBalanceRow,
) -> IssueRecord:
    return statement_issue(
        adapter,
        profile,
        entry,
        provenance,
        StatementIssueDetails(
            kind="instrument_identity_blocked",
            severity="high",
            message=(
                f"{adapter.manifest.display_name} statement evidence could not "
                f"resolve instrument {row.asset}."
            ),
            raw_row_ref=row.raw_row_ref,
            context_timestamp=row_context_timestamp(row),
        ),
    )


def instrument_review(
    adapter: StatementDocumentEvidenceAdapter,
    profile: SourceProfile,
    entry: FileInventoryEntry,
    provenance: ProvenanceLocator,
    row: StatementDocumentBalanceRow,
) -> NormalizationReviewRecord:
    return statement_review(
        adapter,
        profile,
        entry,
        provenance,
        StatementReviewDetails(
            kind="instrument_identity_review",
            message=(
                f"Review required for {adapter.manifest.display_name} statement "
                f"instrument {row.asset}."
            ),
            raw_row_ref=row.raw_row_ref,
            context_timestamp=row_context_timestamp(row),
            field_name="asset",
            original_value=row.asset,
        ),
    )
