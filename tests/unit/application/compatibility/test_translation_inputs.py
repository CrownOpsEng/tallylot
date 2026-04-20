from __future__ import annotations

from tallylot.application.compatibility.translation_inputs import (
    reconstruct_translation_input_plan,
)
from tallylot.application.normalization.translation_inputs.models import (
    TranslationInputPlanningResult,
)
from tallylot.domain.evidence import (
    EvidenceMemberKind,
    EvidenceMemberRecord,
    EvidenceMemberStatus,
    EvidenceSelectionBasis,
    EvidenceSelectionRecord,
    EvidenceSet,
)
from tallylot.ports.translation_inputs import (
    TranslationCoverageMode,
    TranslationCoverageWindow,
    TranslationFreshness,
    TranslationFreshnessKind,
    TranslationInputCandidate,
    TranslationInputPlan,
    TranslationPlanDecision,
    TranslationSelectionMode,
)


def test_reconstruct_translation_input_plan_preserves_same_run_decision_detail() -> (
    None
):
    evidence_set = EvidenceSet(
        evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
        selection_fingerprint="fingerprint",
        capture_manifest_fingerprint="manifest-1",
        evidence_selection_records=(
            EvidenceSelectionRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                key=("retail_activity_export_file",),
                fingerprint="selection-fingerprint",
                basis=EvidenceSelectionBasis.COVERAGE,
            ),
        ),
        evidence_member_records=(
            EvidenceMemberRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                member_id="member-newer",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=("2026-03-23 Statement - All Time.csv", ""),
                status=EvidenceMemberStatus.SELECTED,
                capture_manifest_fingerprint="manifest-1",
            ),
            EvidenceMemberRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                member_id="member-segment",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=("2020 Segment.csv", ""),
                status=EvidenceMemberStatus.SELECTED,
                capture_manifest_fingerprint="manifest-1",
            ),
            EvidenceMemberRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                member_id="member-older",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=("2021 Statement.csv", ""),
                status=EvidenceMemberStatus.SUPERSEDED,
                capture_manifest_fingerprint="manifest-1",
            ),
        ),
        evidence_observation_records=(),
    )
    planning_result = TranslationInputPlanningResult(
        candidates=(
            _candidate("newer", "2026-03-23 Statement - All Time.csv"),
            _candidate("segment", "2020 Segment.csv"),
            _candidate("older", "2021 Statement.csv"),
        ),
        plan=TranslationInputPlan(
            selected_candidate_ids=(
                "coinbase:retail_export:2020 Segment.csv",
                "coinbase:retail_export:2026-03-23 Statement - All Time.csv",
            ),
            decisions=(
                TranslationPlanDecision(
                    candidate_id="coinbase:retail_export:2020 Segment.csv",
                    status="selected",
                    reason="candidate is disjoint within its selection group",
                ),
                TranslationPlanDecision(
                    candidate_id="coinbase:retail_export:2021 Statement.csv",
                    status="superseded_replaced",
                    reason="superseded by the selected translation input candidate",
                    conflicts_with_candidate_ids=(
                        "coinbase:retail_export:2026-03-23 Statement - All Time.csv",
                    ),
                ),
                TranslationPlanDecision(
                    candidate_id="coinbase:retail_export:2026-03-23 Statement - All Time.csv",
                    status="selected",
                    reason="winner selected for deterministic translation input planning",
                    replaces_candidate_ids=(
                        "coinbase:retail_export:2021 Statement.csv",
                    ),
                ),
            ),
            blocked=False,
        ),
        issues=(),
    )

    plan = reconstruct_translation_input_plan(
        evidence_set=evidence_set,
        planning_result=planning_result,
    )

    assert plan.selected_candidate_ids == planning_result.plan.selected_candidate_ids
    assert plan.blocked is False
    assert plan.decisions == planning_result.plan.decisions


def test_reconstruct_translation_input_plan_preserves_candidate_specific_blocked_reason() -> (
    None
):
    evidence_set = EvidenceSet(
        evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
        selection_fingerprint="fingerprint",
        capture_manifest_fingerprint="manifest-1",
        evidence_selection_records=(
            EvidenceSelectionRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                key=("retail_activity_export_file",),
                fingerprint="selection-fingerprint",
                basis=EvidenceSelectionBasis.UPSTREAM_GAP,
                blocking_gap_refs=("translation_input_plan:blocked_invalid_candidate",),
            ),
        ),
        evidence_member_records=(
            EvidenceMemberRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                member_id="member-a",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=("one.csv", ""),
                status=EvidenceMemberStatus.BLOCKED,
                capture_manifest_fingerprint="manifest-1",
            ),
            EvidenceMemberRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                member_id="member-b",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=("two.csv", ""),
                status=EvidenceMemberStatus.BLOCKED,
                capture_manifest_fingerprint="manifest-1",
            ),
        ),
        evidence_observation_records=(),
    )
    planning_result = TranslationInputPlanningResult(
        candidates=(
            _candidate("one", "one.csv"),
            _candidate("two", "two.csv"),
        ),
        plan=TranslationInputPlan(
            selected_candidate_ids=(),
            decisions=(
                TranslationPlanDecision(
                    candidate_id="coinbase:retail_export:one.csv",
                    status="blocked_invalid_candidate",
                    reason="content_fingerprint does not match candidate member inventory",
                    conflicts_with_candidate_ids=("coinbase:retail_export:two.csv",),
                ),
                TranslationPlanDecision(
                    candidate_id="coinbase:retail_export:two.csv",
                    status="blocked_invalid_candidate",
                    reason="candidate id 'two' is duplicated",
                    conflicts_with_candidate_ids=("coinbase:retail_export:one.csv",),
                ),
            ),
            blocked=True,
        ),
        issues=(),
    )

    plan = reconstruct_translation_input_plan(
        evidence_set=evidence_set,
        planning_result=planning_result,
    )

    assert plan.blocked is True
    assert plan.decisions == planning_result.plan.decisions


def test_reconstruct_translation_input_plan_preserves_blocked_reason_from_selection() -> (
    None
):
    evidence_set = EvidenceSet(
        evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
        selection_fingerprint="fingerprint",
        capture_manifest_fingerprint="manifest-1",
        evidence_selection_records=(
            EvidenceSelectionRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                key=("retail_activity_export_file",),
                fingerprint="selection-fingerprint",
                basis=EvidenceSelectionBasis.UPSTREAM_GAP,
                blocking_gap_refs=("translation_input_plan:blocked_unknown_coverage",),
            ),
        ),
        evidence_member_records=(
            EvidenceMemberRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                member_id="member-a",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=("one.csv", ""),
                status=EvidenceMemberStatus.BLOCKED,
                capture_manifest_fingerprint="manifest-1",
            ),
            EvidenceMemberRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                member_id="member-b",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=("two.csv", ""),
                status=EvidenceMemberStatus.BLOCKED,
                capture_manifest_fingerprint="manifest-1",
            ),
        ),
        evidence_observation_records=(),
    )

    plan = reconstruct_translation_input_plan(evidence_set=evidence_set)

    assert not plan.selected_candidate_ids
    assert plan.blocked is True
    assert {decision.status for decision in plan.decisions} == {
        "blocked_unknown_coverage"
    }
    assert {decision.reason for decision in plan.decisions} == {
        "translation input planning cannot compare multiple candidates when any "
        "candidate has unknown event-time coverage"
    }


def _candidate(candidate_id: str, relative_path: str) -> TranslationInputCandidate:
    return TranslationInputCandidate(
        candidate_id=f"coinbase:retail_export:{relative_path}",
        selection_group="coinbase:retail_export",
        family_id="retail_export",
        member_relative_paths=(relative_path,),
        selection_mode=TranslationSelectionMode.REPLACEABLE_RANGE,
        coverage=TranslationCoverageWindow(
            start_at=None,
            start_precision=None,
            end_at=None,
            end_precision=None,
            mode=TranslationCoverageMode.UNKNOWN,
        ),
        freshness=TranslationFreshness(
            kind=TranslationFreshnessKind.UNKNOWN,
            timestamp=None,
            rank=None,
        ),
        content_fingerprint=f"fingerprint:{candidate_id}",
        description=f"candidate {candidate_id}",
        comparison_key="coinbase:retail_export",
        comparable=True,
    )
