from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.claim import (
    ClaimBundleDecisionBasis,
    ClaimBundleDecisionOutcome,
    ClaimBundleDecisionRecord,
    ClaimBundleRecord,
    ClaimKind,
    ClaimRecord,
    ClaimRecordStatus,
    ClaimSet,
)
from tallylot.domain.economics import (
    EconomicEventKind,
    EconomicEventRecord,
    EconomicFacts,
    EconomicLegRecord,
    EconomicLegRole,
    LifecycleEvent,
    SettlementStatus,
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
from tallylot.domain.reconciliation import CheckpointProposalStatus, ComparisonOutcome
from tallylot.domain.reconciliation import reconciliation_state_fingerprint
from tallylot.domain.temporal import TemporalPrecision

from tallylot.application.reconciliation import build_reconciliation_states


def test_builder_groups_position_segments_and_derives_exact_targets() -> None:
    claim_set, evidence_set, economic_facts = _matched_fixture()

    states = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )

    assert len(states) == 1
    state = states[0]
    assert state.economic_facts_ref == economic_facts.economic_facts_id
    assert state.continuity_segment_records[0].status.value == "complete"
    assert (
        state.balance_target_records[0].comparison_outcome is ComparisonOutcome.MATCHED
    )
    assert state.checkpoint_proposal_records[0].status is CheckpointProposalStatus.READY


def test_builder_marks_mismatched_targets_as_blocked() -> None:
    claim_set, evidence_set, economic_facts = _matched_fixture(observed_quantity="2.00")

    states = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )

    assert (
        states[0].balance_target_records[0].comparison_outcome
        is ComparisonOutcome.MISMATCHED
    )
    assert (
        states[0].checkpoint_proposal_records[0].status
        is CheckpointProposalStatus.BLOCKED
    )


def test_builder_marks_missing_observation_support_as_partial() -> None:
    claim_set, evidence_set, economic_facts = _matched_fixture(
        with_observation_refs=False
    )

    states = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )

    assert (
        states[0].checkpoint_proposal_records[0].status
        is CheckpointProposalStatus.PARTIAL
    )


def test_builder_ignores_unknown_observation_refs() -> None:
    claim_set, evidence_set, economic_facts = _matched_fixture(
        observation_refs=("missing-observation",)
    )

    states = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )

    assert states[0].checkpoint_proposal_records[0].evidence_refs == ()
    assert (
        states[0].checkpoint_proposal_records[0].status
        is CheckpointProposalStatus.PARTIAL
    )


def test_builder_emits_partial_segment_when_only_economic_activity_exists() -> None:
    claim_set, evidence_set, economic_facts = _matched_fixture()
    claim_set = ClaimSet(
        claim_set_id=claim_set.claim_set_id,
        evidence_set_ref=claim_set.evidence_set_ref,
        emitter_id=claim_set.emitter_id,
        claim_records=tuple(
            claim
            for claim in claim_set.claim_records
            if claim.kind is not ClaimKind.BALANCE
        ),
        claim_bundle_records=(),
        claim_bundle_decision_records=(),
    )

    states = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )

    assert len(states) == 1
    assert states[0].continuity_segment_records[0].status.value == "partial"
    assert states[0].balance_target_records == ()
    assert states[0].checkpoint_proposal_records == ()


def test_build_reconciliation_states_replay_with_unchanged_inputs_preserves_payload_and_fingerprint() -> (
    None
):
    claim_set, evidence_set, economic_facts = _matched_fixture()

    first = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )
    second = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )

    assert len(first) == len(second)
    assert tuple(state.reconciliation_state_id for state in first) == tuple(
        state.reconciliation_state_id for state in second
    )
    assert tuple(state.to_payload() for state in first) == tuple(
        state.to_payload() for state in second
    )
    assert tuple(reconciliation_state_fingerprint(state) for state in first) == tuple(
        reconciliation_state_fingerprint(state) for state in second
    )
    assert tuple(
        state.continuity_segment_records[0].segment_id for state in first
    ) == tuple(state.continuity_segment_records[0].segment_id for state in second)
    assert tuple(
        target.target_id for state in first for target in state.balance_target_records
    ) == tuple(
        target.target_id for state in second for target in state.balance_target_records
    )
    assert tuple(
        proposal.proposal_id
        for state in first
        for proposal in state.checkpoint_proposal_records
    ) == tuple(
        proposal.proposal_id
        for state in second
        for proposal in state.checkpoint_proposal_records
    )


def test_build_reconciliation_states_order_only_changes_do_not_change_ids_payload_or_fingerprint() -> (
    None
):
    claim_set, evidence_set, economic_facts = _matched_fixture()
    reordered_claim_set = ClaimSet(
        claim_set_id=claim_set.claim_set_id,
        evidence_set_ref=claim_set.evidence_set_ref,
        emitter_id=claim_set.emitter_id,
        claim_records=tuple(reversed(claim_set.claim_records)),
        claim_bundle_records=tuple(reversed(claim_set.claim_bundle_records)),
        claim_bundle_decision_records=tuple(
            reversed(claim_set.claim_bundle_decision_records)
        ),
    )
    reordered_evidence_set = EvidenceSet(
        evidence_set_id=evidence_set.evidence_set_id,
        selection_fingerprint=evidence_set.selection_fingerprint,
        capture_manifest_fingerprint=evidence_set.capture_manifest_fingerprint,
        evidence_selection_records=tuple(
            reversed(evidence_set.evidence_selection_records)
        ),
        evidence_member_records=tuple(reversed(evidence_set.evidence_member_records)),
        evidence_observation_records=tuple(
            reversed(evidence_set.evidence_observation_records)
        ),
    )
    reordered_economic_facts = EconomicFacts(
        economic_facts_id=economic_facts.economic_facts_id,
        claim_set_refs=economic_facts.claim_set_refs,
        economic_event_records=tuple(reversed(economic_facts.economic_event_records)),
        economic_leg_records=tuple(reversed(economic_facts.economic_leg_records)),
        valuation_records=economic_facts.valuation_records,
    )

    first = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )
    second = build_reconciliation_states(
        economic_facts=reordered_economic_facts,
        claim_set=reordered_claim_set,
        evidence_set=reordered_evidence_set,
    )

    assert tuple(state.reconciliation_state_id for state in first) == tuple(
        state.reconciliation_state_id for state in second
    )
    assert tuple(state.to_payload() for state in first) == tuple(
        state.to_payload() for state in second
    )
    assert tuple(reconciliation_state_fingerprint(state) for state in first) == tuple(
        reconciliation_state_fingerprint(state) for state in second
    )
    assert tuple(
        target.target_id for state in first for target in state.balance_target_records
    ) == tuple(
        target.target_id for state in second for target in state.balance_target_records
    )
    assert tuple(
        proposal.proposal_id
        for state in first
        for proposal in state.checkpoint_proposal_records
    ) == tuple(
        proposal.proposal_id
        for state in second
        for proposal in state.checkpoint_proposal_records
    )


def test_builder_ignores_unaccepted_balance_claim_bundles() -> None:
    claim_set, evidence_set, economic_facts = _matched_fixture()
    claim_set = ClaimSet(
        claim_set_id=claim_set.claim_set_id,
        evidence_set_ref=claim_set.evidence_set_ref,
        emitter_id=claim_set.emitter_id,
        claim_records=claim_set.claim_records,
        claim_bundle_records=claim_set.claim_bundle_records,
        claim_bundle_decision_records=(
            ClaimBundleDecisionRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-balance",
                decision_id="decision-balance",
                outcome=ClaimBundleDecisionOutcome.BLOCKED,
                accepted_bundle_ref="",
                rejected_bundle_refs=("bundle-balance",),
                deferred_bundle_refs=(),
                basis=ClaimBundleDecisionBasis.POLICY_DECISION_REQUIRED,
                blocking_gap_refs=("gap:statement-selection",),
            ),
        ),
    )

    states = build_reconciliation_states(
        economic_facts=economic_facts,
        claim_set=claim_set,
        evidence_set=evidence_set,
    )

    assert len(states) == 1
    assert states[0].continuity_segment_records[0].status.value == "partial"
    assert states[0].balance_target_records == ()
    assert states[0].checkpoint_proposal_records == ()


def _matched_fixture(
    *,
    observed_quantity: str = "1.25",
    with_observation_refs: bool = True,
    observation_refs: tuple[str, ...] | None = None,
) -> tuple[ClaimSet, EvidenceSet, EconomicFacts]:
    subject_ref = (
        "position",
        (
            ("beneficial_owner:filing",),
            ("coinbase",),
            ("symbol:BTC@coinbase",),
            None,
            "held_position",
        ),
    )
    observed_at = datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC)
    claim_set = ClaimSet(
        claim_set_id="claim-set-1",
        evidence_set_ref="evidence-1",
        emitter_id="coinbase:claim",
        claim_records=(
            ClaimRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-balance",
                bundle_id="bundle-balance",
                claim_id="claim-balance",
                kind=ClaimKind.BALANCE,
                status=ClaimRecordStatus.ASSERTED,
                key=("balance",),
                member_refs=("member-statement",),
                observation_refs=(
                    observation_refs
                    if observation_refs is not None
                    else (
                        ("observation-document", "observation-row")
                        if with_observation_refs
                        else ()
                    )
                ),
                effective_at=None,
                precision=TemporalPrecision.TIMESTAMP,
                provenance_refs=("statement:row:1",),
                location_claim_ref="claim-location",
                instrument_claim_refs=("claim-instrument",),
                balance_kind="asset_balance",
                quantity=Decimal(observed_quantity),
                observed_at=observed_at,
            ),
            ClaimRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-balance",
                bundle_id="bundle-balance",
                claim_id="claim-instrument",
                kind=ClaimKind.INSTRUMENT,
                status=ClaimRecordStatus.ASSERTED,
                key=("instrument",),
                member_refs=("member-statement",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=("statement:row:1",),
                scheme="symbol",
                value="BTC",
                venue="coinbase",
                instrument_kind="crypto",
                name="Bitcoin",
            ),
            ClaimRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-balance",
                bundle_id="bundle-balance",
                claim_id="claim-location",
                kind=ClaimKind.LOCATION,
                status=ClaimRecordStatus.ASSERTED,
                key=("location",),
                member_refs=("member-statement",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=("statement:row:1",),
                location_ref="coinbase",
                location_group_label="Coinbase",
                location_label="Coinbase",
            ),
            ClaimRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-balance",
                bundle_id="bundle-balance",
                claim_id="claim-owner",
                kind=ClaimKind.BENEFICIAL_OWNER,
                status=ClaimRecordStatus.ASSERTED,
                key=("owner",),
                member_refs=("member-statement",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=("statement:row:1",),
                beneficial_owner_ref="beneficial_owner:filing",
            ),
        ),
        claim_bundle_records=(
            ClaimBundleRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-balance",
                bundle_id="bundle-balance",
                key="statement-row-1",
                scope_key=("member-statement", "statement-row-1"),
                claim_refs=(
                    "claim-balance",
                    "claim-instrument",
                    "claim-location",
                    "claim-owner",
                ),
            ),
        ),
        claim_bundle_decision_records=(
            ClaimBundleDecisionRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-balance",
                decision_id="decision-balance",
                outcome=ClaimBundleDecisionOutcome.ACCEPTED,
                accepted_bundle_ref="bundle-balance",
                rejected_bundle_refs=(),
                deferred_bundle_refs=(),
                basis=ClaimBundleDecisionBasis.SINGLE_BUNDLE,
                blocking_gap_refs=(),
            ),
        ),
    )
    evidence_set = EvidenceSet(
        evidence_set_id="evidence-1",
        selection_fingerprint="selection-1",
        capture_manifest_fingerprint="manifest-1",
        evidence_selection_records=(
            EvidenceSelectionRecord(
                evidence_set_id="evidence-1",
                selection_id="selection-1",
                key=("statement_document", "statement.pdf"),
                fingerprint="fingerprint-1",
                basis=EvidenceSelectionBasis.SINGLE_MEMBER,
            ),
        ),
        evidence_member_records=(
            EvidenceMemberRecord(
                evidence_set_id="evidence-1",
                selection_id="selection-1",
                member_id="member-statement",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.STATEMENT_DOCUMENT_FILE,
                locator=("statement.pdf",),
                status=EvidenceMemberStatus.SELECTED,
                capture_manifest_fingerprint="manifest-1",
            ),
        ),
        evidence_observation_records=(
            EvidenceObservationRecord(
                evidence_set_id="evidence-1",
                member_id="member-statement",
                observation_id="observation-document",
                kind=EvidenceObservationKind.STATEMENT_DOCUMENT,
                key=("document",),
                statement_kind="coinbase",
                document_effective_at=observed_at,
                document_effective_precision=TemporalPrecision.TIMESTAMP,
                statement_as_of=observed_at,
                statement_as_of_precision=TemporalPrecision.TIMESTAMP,
                provenance_refs=(("capture-1", "statement.pdf"),),
            ),
            EvidenceObservationRecord(
                evidence_set_id="evidence-1",
                member_id="member-statement",
                observation_id="observation-row",
                kind=EvidenceObservationKind.STATEMENT_BALANCE_ROW,
                key=("row-1",),
                observed_at=observed_at,
                precision=TemporalPrecision.TIMESTAMP,
                provenance_refs=(("capture-1", "statement.pdf#row-1"),),
                location_group_label="Coinbase",
                location_label="Coinbase",
                balance_kind="asset_balance",
                instrument_symbol="BTC",
                quantity=Decimal(observed_quantity),
                notes="Statement row",
            ),
        ),
    )
    economic_facts = EconomicFacts(
        economic_facts_id="facts-1",
        claim_set_refs=("claim-set-1",),
        economic_event_records=(
            EconomicEventRecord(
                event_id='["bundle-activity",0]',
                claim_bundle_id="bundle-activity",
                claim_bundle_decision_id="decision-activity",
                kind=EconomicEventKind.ASSET_MOVEMENT,
                effective_at=datetime(2024, 2, 8, 16, 31, 22, tzinfo=UTC),
                recorded_at=datetime(2024, 2, 8, 16, 31, 22, tzinfo=UTC),
                settlement_status=SettlementStatus.SETTLED,
                lifecycle_event=LifecycleEvent.CREATED,
                beneficial_owner_ref="beneficial_owner:filing",
            ),
        ),
        economic_leg_records=(
            EconomicLegRecord(
                leg_id=(
                    '["["bundle-activity",0]","holding_change",'
                    '["position",[["beneficial_owner:filing"],["coinbase"],'
                    '["symbol:BTC@coinbase"],null,"held_position"]],0]'
                ),
                event_id='["bundle-activity",0]',
                role=EconomicLegRole.HOLDING_CHANGE,
                subject_ref=subject_ref,
                instrument_ref=("symbol:BTC@coinbase",),
                location_ref=("coinbase",),
                quantity=Decimal("1.25"),
            ),
        ),
        valuation_records=(),
    )
    return claim_set, evidence_set, economic_facts
