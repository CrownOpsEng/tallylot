from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from tallylot.domain.economics import (
    ECONOMIC_FACTS_SCHEMA_VERSION,
    EconomicEventKind,
    EconomicEventRecord,
    EconomicFacts,
    EconomicLegRecord,
    EconomicLegRole,
    LifecycleEvent,
    SettlementStatus,
    canonical_economic_event_records,
    canonical_economic_leg_records,
    economic_facts_fingerprint,
    stable_economic_facts_id,
    stable_event_id,
    stable_leg_id,
)


def _sample_subject_ref() -> tuple[str, tuple[object, ...]]:
    return (
        "position",
        (("owner:1",), ("location:1",), ("instrument:1",), None, "held_position"),
    )


def test_economic_facts_payload_and_fingerprint_are_stable() -> None:
    event_id = stable_event_id("bundle-1", 0)
    subject_ref = _sample_subject_ref()
    facts = EconomicFacts(
        economic_facts_id=stable_economic_facts_id(("claim-set-ref",)),
        claim_set_refs=("claim-set-ref",),
        economic_event_records=(
            EconomicEventRecord(
                event_id=event_id,
                claim_bundle_id="bundle-1",
                claim_bundle_decision_id="decision-1",
                kind=EconomicEventKind.ASSET_MOVEMENT,
                effective_at=datetime(2026, 3, 23, tzinfo=UTC),
                recorded_at=datetime(2026, 3, 23, tzinfo=UTC),
                settlement_status=SettlementStatus.SETTLED,
                lifecycle_event=LifecycleEvent.CREATED,
                beneficial_owner_ref="owner:1",
            ),
        ),
        economic_leg_records=(
            EconomicLegRecord(
                leg_id=stable_leg_id(
                    event_id, EconomicLegRole.HOLDING_CHANGE, subject_ref, 0
                ),
                event_id=event_id,
                role=EconomicLegRole.HOLDING_CHANGE,
                subject_ref=subject_ref,
                instrument_ref=("instrument:1",),
                location_ref=("location:1",),
                quantity=Decimal("1.2500"),
            ),
        ),
        valuation_records=(),
    )

    payload = facts.to_payload()

    assert payload["schema_version"] == ECONOMIC_FACTS_SCHEMA_VERSION
    assert payload["valuation_records"] == []
    leg_payloads = cast(list[dict[str, object]], payload["economic_leg_records"])
    assert isinstance(leg_payloads, list)
    assert leg_payloads[0]["quantity"] == "1.25"
    assert economic_facts_fingerprint(facts) == economic_facts_fingerprint(facts)


def test_economic_leg_rejects_zero_quantity() -> None:
    try:
        EconomicLegRecord(
            leg_id="leg-1",
            event_id="event-1",
            role=EconomicLegRole.HOLDING_CHANGE,
            subject_ref=_sample_subject_ref(),
            instrument_ref=("instrument:1",),
            location_ref=("location:1",),
            quantity=Decimal("0"),
        )
    except ValueError as error:
        assert str(error) == "economic leg quantity must not be zero"
    else:
        raise AssertionError("expected zero-quantity leg to fail")


def test_stable_ids_and_canonical_ordering_follow_declared_contract() -> None:
    first_event_id = stable_event_id("bundle-b", 0)
    second_event_id = stable_event_id("bundle-a", 0)
    later = datetime(2026, 3, 24, tzinfo=UTC)
    earlier = datetime(2026, 3, 23, tzinfo=UTC)
    subject_ref = _sample_subject_ref()
    second_leg = EconomicLegRecord(
        leg_id=stable_leg_id(first_event_id, EconomicLegRole.FEE, subject_ref, 1),
        event_id=first_event_id,
        role=EconomicLegRole.FEE,
        subject_ref=subject_ref,
        instrument_ref=("instrument:1",),
        location_ref=("location:1",),
        quantity=Decimal("-0.10"),
    )
    first_leg = EconomicLegRecord(
        leg_id=stable_leg_id(
            second_event_id, EconomicLegRole.HOLDING_CHANGE, subject_ref, 0
        ),
        event_id=second_event_id,
        role=EconomicLegRole.HOLDING_CHANGE,
        subject_ref=subject_ref,
        instrument_ref=("instrument:1",),
        location_ref=("location:1",),
        quantity=Decimal("1.00"),
    )

    economic_facts_id = stable_economic_facts_id(("claim-set-b", "claim-set-a"))

    assert economic_facts_id == stable_economic_facts_id(("claim-set-a", "claim-set-b"))
    assert len(economic_facts_id) == 64
    assert "/" not in economic_facts_id
    assert canonical_economic_event_records(
        (
            EconomicEventRecord(
                event_id=first_event_id,
                claim_bundle_id="bundle-b",
                claim_bundle_decision_id="decision-b",
                kind=EconomicEventKind.ASSET_MOVEMENT,
                effective_at=later,
                recorded_at=later,
                settlement_status=SettlementStatus.SETTLED,
                lifecycle_event=LifecycleEvent.CREATED,
            ),
            EconomicEventRecord(
                event_id=second_event_id,
                claim_bundle_id="bundle-a",
                claim_bundle_decision_id="decision-a",
                kind=EconomicEventKind.FEE_OR_REBATE,
                effective_at=earlier,
                recorded_at=earlier,
                settlement_status=SettlementStatus.SETTLED,
                lifecycle_event=LifecycleEvent.MIGRATED,
            ),
        )
    ) == (
        EconomicEventRecord(
            event_id=second_event_id,
            claim_bundle_id="bundle-a",
            claim_bundle_decision_id="decision-a",
            kind=EconomicEventKind.FEE_OR_REBATE,
            effective_at=earlier,
            recorded_at=earlier,
            settlement_status=SettlementStatus.SETTLED,
            lifecycle_event=LifecycleEvent.MIGRATED,
        ),
        EconomicEventRecord(
            event_id=first_event_id,
            claim_bundle_id="bundle-b",
            claim_bundle_decision_id="decision-b",
            kind=EconomicEventKind.ASSET_MOVEMENT,
            effective_at=later,
            recorded_at=later,
            settlement_status=SettlementStatus.SETTLED,
            lifecycle_event=LifecycleEvent.CREATED,
        ),
    )
    assert canonical_economic_leg_records((second_leg, first_leg)) == (
        first_leg,
        second_leg,
    )
