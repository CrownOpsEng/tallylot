"""Statement-document EvidenceSet record assembly."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.application.evidence.statement_extraction import (
    CollectedStatementDocument,
    StatementDocumentCollectionResult,
)
from tallylot.domain.evidence import (
    EvidenceMemberKind,
    EvidenceMemberRecord,
    EvidenceMemberStatus,
    EvidenceObservationKind,
    EvidenceObservationRecord,
    EvidenceSelectionBasis,
    EvidenceSelectionRecord,
)
from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import SourceProfile


@dataclass(frozen=True)
class PendingObservation:
    member_kind: EvidenceMemberKind
    member_locator: tuple[str, ...]
    record: EvidenceObservationRecord


def build_statement_records(
    *,
    profile: SourceProfile,
    capture_uid: str,
    capture_manifest_fingerprint: str,
    documents: StatementDocumentCollectionResult,
) -> tuple[
    tuple[EvidenceSelectionRecord, ...],
    tuple[EvidenceMemberRecord, ...],
    tuple[PendingObservation, ...],
]:
    selections: list[EvidenceSelectionRecord] = []
    members: list[EvidenceMemberRecord] = []
    observations: list[PendingObservation] = []
    for document in documents.collected_documents:
        key = ("statement_document", *document.locator)
        selections.append(
            EvidenceSelectionRecord(
                evidence_set_id="",
                selection_id="",
                key=key,
                fingerprint="",
                basis=_statement_selection_basis(
                    document=document, documents=documents
                ),
                blocking_gap_refs=_statement_blocking_gap_refs(
                    document=document,
                    documents=documents,
                ),
            )
        )
        members.append(
            EvidenceMemberRecord(
                evidence_set_id="",
                selection_id="",
                member_id="",
                source_slug=str(profile.source),
                adapter_id=str(profile.adapter_id),
                capture_uid=capture_uid,
                kind=EvidenceMemberKind.STATEMENT_DOCUMENT_FILE,
                locator=document.locator,
                status=document.member_status,
                capture_manifest_fingerprint=capture_manifest_fingerprint,
            )
        )
        if not document.selected:
            continue
        observations.append(
            PendingObservation(
                member_kind=EvidenceMemberKind.STATEMENT_DOCUMENT_FILE,
                member_locator=document.locator,
                record=EvidenceObservationRecord(
                    evidence_set_id="",
                    member_id="",
                    observation_id="",
                    kind=EvidenceObservationKind.STATEMENT_DOCUMENT,
                    key=("document",),
                    provenance_refs=(),
                    statement_kind=str(profile.adapter_id),
                    document_effective_at=document.parsed.document_effective_at,
                    document_effective_precision=document.document_effective_precision,
                    statement_as_of=document.parsed.statement_as_of_at,
                    statement_as_of_precision=document.statement_as_of_precision,
                ),
            )
        )
        for index, row in enumerate(document.parsed.rows):
            row_key = row.raw_row_ref or f"row:{index}"
            observations.append(
                PendingObservation(
                    member_kind=EvidenceMemberKind.STATEMENT_DOCUMENT_FILE,
                    member_locator=document.locator,
                    record=EvidenceObservationRecord(
                        evidence_set_id="",
                        member_id="",
                        observation_id="",
                        kind=EvidenceObservationKind.STATEMENT_BALANCE_ROW,
                        key=(row_key,),
                        observed_at=row.as_of_at,
                        precision=row.as_of_precision,
                        provenance_refs=(),
                        location_group_label=row.account,
                        location_label=row.wallet,
                        balance_kind=row.balance_kind,
                        instrument_symbol=row.asset,
                        quantity=row.quantity,
                        notes=row.notes,
                        staked_quantity_text=row.staked_quantity,
                        value_amount_text=row.value_amount,
                        value_currency=row.value_currency,
                        price_amount_text=row.price_amount,
                        price_currency=row.price_currency,
                    ),
                )
            )
    return tuple(selections), tuple(members), tuple(observations)


def _statement_selection_basis(
    *,
    document: CollectedStatementDocument,
    documents: StatementDocumentCollectionResult,
) -> EvidenceSelectionBasis:
    issue_kinds = {
        issue.kind
        for issue in documents.issues
        if _issue_matches_statement_document(issue, document)
    }
    if "statement_document_ambiguous" in issue_kinds:
        return EvidenceSelectionBasis.AMBIGUOUS_OVERLAP
    if "statement_document_missing_as_of" in issue_kinds:
        return EvidenceSelectionBasis.UPSTREAM_GAP
    if document.member_status is EvidenceMemberStatus.SUPERSEDED:
        return EvidenceSelectionBasis.FRESHNESS
    if document.selected and any(
        item.member_status is EvidenceMemberStatus.SUPERSEDED
        for item in documents.collected_documents
    ):
        return EvidenceSelectionBasis.FRESHNESS
    return EvidenceSelectionBasis.SINGLE_MEMBER


def _statement_blocking_gap_refs(
    *,
    document: CollectedStatementDocument,
    documents: StatementDocumentCollectionResult,
) -> tuple[str, ...]:
    if document.member_status is not EvidenceMemberStatus.BLOCKED:
        return ()
    return tuple(
        sorted(
            issue.issue_id
            for issue in documents.issues
            if _issue_matches_statement_document(issue, document)
            and issue.kind
            in {"statement_document_ambiguous", "statement_document_missing_as_of"}
        )
    )


def _issue_matches_statement_document(
    issue: IssueRecord,
    document: CollectedStatementDocument,
) -> bool:
    if issue.raw_provenance is not None:
        return issue.raw_provenance.relative_path == (
            document.entry.archive_source_path or document.entry.relative_path
        ) and (issue.raw_provenance.archive_member_path or "") == (
            document.entry.archive_member_path or ""
        )
    return issue.raw_file == document.entry.relative_path
