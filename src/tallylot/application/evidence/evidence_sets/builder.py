"""Bounded EvidenceSet builder."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

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
    EvidenceSet,
)
from tallylot.domain.evidence.models import (
    selection_fingerprint_for_records,
    selection_record_fingerprints,
    stable_evidence_set_id,
    stable_member_id,
    stable_observation_id,
    stable_selection_id,
)
from tallylot.ports.source_profiles import SourceProfile

if TYPE_CHECKING:
    from tallylot.application.normalization.translation_inputs.models import (
        TranslationInputPlanningResult,
    )


@dataclass(frozen=True)
class _PendingObservation:
    member_kind: EvidenceMemberKind
    member_locator: tuple[str, ...]
    record: EvidenceObservationRecord


def build_evidence_set_for_profile(
    *,
    profile: SourceProfile,
    capture_uid: str,
    capture_manifest_fingerprint: str,
    planner_result: TranslationInputPlanningResult,
    statement_documents: StatementDocumentCollectionResult,
) -> EvidenceSet | None:
    if str(profile.adapter_id) != "coinbase":
        return None
    selections = _retail_selection_records(planner_result)
    members = _retail_member_records(
        profile=profile,
        capture_uid=capture_uid,
        capture_manifest_fingerprint=capture_manifest_fingerprint,
        planner_result=planner_result,
    )
    statement_selections, statement_members, statement_observations = (
        _statement_records(
            profile=profile,
            capture_uid=capture_uid,
            capture_manifest_fingerprint=capture_manifest_fingerprint,
            documents=statement_documents,
        )
    )
    all_selections = (*selections, *statement_selections)
    all_members = (*members, *statement_members)
    all_pending_observations = statement_observations
    all_observations = tuple(
        observation.record for observation in all_pending_observations
    )

    provisional_set_id = stable_evidence_set_id(
        source_slug=str(profile.source),
        adapter_id=str(profile.adapter_id),
        capture_uid=capture_uid,
        selection_fingerprint=selection_fingerprint_for_records(
            selections=tuple(all_selections),
            members=tuple(all_members),
            observations=tuple(all_observations),
        ),
    )
    selection_ids_by_key = {
        selection.key: stable_selection_id(
            evidence_set_id=provisional_set_id,
            key=selection.key,
        )
        for selection in all_selections
    }
    members_with_ids = tuple(
        replace(
            member,
            evidence_set_id=provisional_set_id,
            selection_id=selection_ids_by_key[member_selection_key(member)],
            member_id=stable_member_id(
                evidence_set_id=provisional_set_id,
                kind=member.kind,
                locator=member.locator,
            ),
        )
        for member in all_members
    )
    member_ids_by_locator = {
        (member.kind, member.locator): member.member_id for member in members_with_ids
    }
    observations_with_ids = tuple(
        replace(
            observation.record,
            evidence_set_id=provisional_set_id,
            member_id=member_ids_by_locator[
                (observation.member_kind, observation.member_locator)
            ],
            observation_id=stable_observation_id(
                member_id=member_ids_by_locator[
                    (observation.member_kind, observation.member_locator)
                ],
                kind=observation.record.kind,
                key=_observation_identity_key(observation.record),
            ),
        )
        for observation in all_pending_observations
    )
    selections_with_ids = tuple(
        replace(
            selection,
            evidence_set_id=provisional_set_id,
            selection_id=selection_ids_by_key[selection.key],
        )
        for selection in all_selections
    )
    selection_fingerprints = selection_record_fingerprints(
        selections=selections_with_ids,
        members=members_with_ids,
        observations=observations_with_ids,
    )
    finalized_selections = tuple(
        replace(selection, fingerprint=selection_fingerprints[selection.selection_id])
        for selection in selections_with_ids
    )
    selection_fingerprint = selection_fingerprint_for_records(
        selections=finalized_selections,
        members=members_with_ids,
        observations=observations_with_ids,
    )
    evidence_set_id = stable_evidence_set_id(
        source_slug=str(profile.source),
        adapter_id=str(profile.adapter_id),
        capture_uid=capture_uid,
        selection_fingerprint=selection_fingerprint,
    )
    if evidence_set_id != provisional_set_id:
        finalized_selections = tuple(
            replace(
                selection,
                evidence_set_id=evidence_set_id,
                selection_id=stable_selection_id(
                    evidence_set_id=evidence_set_id, key=selection.key
                ),
            )
            for selection in finalized_selections
        )
        selection_ids_by_key = {
            selection.key: selection.selection_id for selection in finalized_selections
        }
        members_with_ids = tuple(
            replace(
                member,
                evidence_set_id=evidence_set_id,
                selection_id=selection_ids_by_key[member_selection_key(member)],
                member_id=stable_member_id(
                    evidence_set_id=evidence_set_id,
                    kind=member.kind,
                    locator=member.locator,
                ),
            )
            for member in all_members
        )
        member_ids_by_locator = {
            (member.kind, member.locator): member.member_id
            for member in members_with_ids
        }
        observations_with_ids = tuple(
            replace(
                observation.record,
                evidence_set_id=evidence_set_id,
                member_id=member_ids_by_locator[
                    (observation.member_kind, observation.member_locator)
                ],
                observation_id=stable_observation_id(
                    member_id=member_ids_by_locator[
                        (observation.member_kind, observation.member_locator)
                    ],
                    kind=observation.record.kind,
                    key=_observation_identity_key(observation.record),
                ),
            )
            for observation in all_pending_observations
        )
    return EvidenceSet(
        evidence_set_id=evidence_set_id,
        selection_fingerprint=selection_fingerprint,
        capture_manifest_fingerprint=capture_manifest_fingerprint,
        evidence_selection_records=tuple(
            sorted(finalized_selections, key=lambda item: item.selection_id)
        ),
        evidence_member_records=tuple(
            sorted(
                members_with_ids,
                key=lambda item: (item.selection_id, item.status.value, item.member_id),
            )
        ),
        evidence_observation_records=tuple(
            sorted(
                observations_with_ids,
                key=lambda item: (item.member_id, item.observation_id),
            )
        ),
    )


def _retail_selection_records(
    planner_result: TranslationInputPlanningResult,
) -> tuple[EvidenceSelectionRecord, ...]:
    return (
        EvidenceSelectionRecord(
            evidence_set_id="",
            selection_id="",
            key=("retail_activity_export_file",),
            fingerprint="",
            basis=_retail_selection_basis(planner_result),
            blocking_gap_refs=_retail_selection_gap_refs(planner_result),
        ),
    )


def _retail_selection_basis(
    planner_result: TranslationInputPlanningResult,
) -> EvidenceSelectionBasis:
    selected = [
        decision
        for decision in planner_result.plan.decisions
        if decision.status == "selected"
    ]
    if selected and not selected[0].replaces_candidate_ids:
        return EvidenceSelectionBasis.SINGLE_MEMBER
    if any(
        decision.status == "superseded_identical"
        for decision in planner_result.plan.decisions
    ):
        return EvidenceSelectionBasis.DUPLICATE
    if any(
        decision.status == "superseded_replaced"
        for decision in planner_result.plan.decisions
    ):
        return EvidenceSelectionBasis.COVERAGE
    if selected:
        return EvidenceSelectionBasis.FRESHNESS
    if any(
        decision.status in {"blocked_partial_overlap", "blocked_ambiguous_freshness"}
        for decision in planner_result.plan.decisions
    ):
        return EvidenceSelectionBasis.AMBIGUOUS_OVERLAP
    return EvidenceSelectionBasis.UPSTREAM_GAP


def _retail_selection_gap_refs(
    planner_result: TranslationInputPlanningResult,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                f"translation_input_plan:{decision.status}"
                for decision in planner_result.plan.decisions
                if decision.status.startswith("blocked")
            }
        )
    )


def _retail_member_records(
    *,
    profile: SourceProfile,
    capture_uid: str,
    capture_manifest_fingerprint: str,
    planner_result: TranslationInputPlanningResult,
) -> tuple[EvidenceMemberRecord, ...]:
    members: list[EvidenceMemberRecord] = []
    for candidate in planner_result.candidates:
        decision = next(
            item
            for item in planner_result.plan.decisions
            if item.candidate_id == candidate.candidate_id
        )
        members.append(
            EvidenceMemberRecord(
                evidence_set_id="",
                selection_id="",
                member_id="",
                source_slug=str(profile.source),
                adapter_id=str(profile.adapter_id),
                capture_uid=capture_uid,
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=(candidate.member_relative_paths[0], ""),
                status=_retail_member_status(decision.status),
                capture_manifest_fingerprint=capture_manifest_fingerprint,
            )
        )
    return tuple(sorted(members, key=lambda item: item.locator))


def _retail_member_status(status: str) -> EvidenceMemberStatus:
    if status == "selected":
        return EvidenceMemberStatus.SELECTED
    if status.startswith("superseded"):
        return EvidenceMemberStatus.SUPERSEDED
    return EvidenceMemberStatus.BLOCKED


def _statement_records(
    *,
    profile: SourceProfile,
    capture_uid: str,
    capture_manifest_fingerprint: str,
    documents: StatementDocumentCollectionResult,
) -> tuple[
    tuple[EvidenceSelectionRecord, ...],
    tuple[EvidenceMemberRecord, ...],
    tuple[_PendingObservation, ...],
]:
    selections: list[EvidenceSelectionRecord] = []
    members: list[EvidenceMemberRecord] = []
    observations: list[_PendingObservation] = []
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
            _PendingObservation(
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
                _PendingObservation(
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


def member_selection_key(member: EvidenceMemberRecord) -> tuple[str, ...]:
    if member.kind is EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE:
        return ("retail_activity_export_file",)
    return ("statement_document", *member.locator)


def _statement_selection_basis(
    *,
    document: CollectedStatementDocument,
    documents: StatementDocumentCollectionResult,
) -> EvidenceSelectionBasis:
    issue_kinds = {
        issue.kind
        for issue in documents.issues
        if issue.raw_file == document.entry.relative_path
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
            if issue.raw_file == document.entry.relative_path
            and issue.kind
            in {"statement_document_ambiguous", "statement_document_missing_as_of"}
        )
    )


def _observation_identity_key(
    observation: EvidenceObservationRecord,
) -> tuple[str, ...]:
    return observation.key
