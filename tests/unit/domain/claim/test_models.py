from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

import pytest

from tallylot.domain.claim import (
    CLAIM_SET_SCHEMA_VERSION,
    ClaimBundleDecisionBasis,
    ClaimBundleDecisionOutcome,
    ClaimBundleDecisionRecord,
    ClaimBundleRecord,
    ClaimKind,
    ClaimLegSpec,
    ClaimRecord,
    ClaimRecordStatus,
    ClaimSet,
)
from tallylot.domain.claim.models import (
    canonical_claim_bundle_decision_records,
    canonical_claim_bundle_records,
    canonical_claim_records,
    claim_set_fingerprint,
    stable_claim_bundle_decision_id,
    stable_claim_bundle_id,
    stable_claim_id,
    stable_claim_scope_id,
    stable_claim_set_id,
)
from tallylot.domain.temporal import TemporalPrecision


def _activity_claim(*, claim_id: str = "claim-activity") -> ClaimRecord:
    return ClaimRecord(
        claim_set_id="claim-set-1",
        scope_id="scope-1",
        bundle_id="bundle-1",
        claim_id=claim_id,
        kind=ClaimKind.ACTIVITY,
        status=ClaimRecordStatus.ASSERTED,
        key=("scope-key", "activity", "0"),
        member_refs=("member-b", "member-a"),
        observation_refs=("observation-b", "observation-a"),
        effective_at=datetime(2026, 3, 23, 12, 0, tzinfo=UTC),
        precision=TemporalPrecision.TIMESTAMP,
        provenance_refs=("prov-b", "prov-a"),
        activity_label="buy",
        location_claim_ref="claim-location",
        leg_specs=(
            ClaimLegSpec(
                slot=1,
                role="asset_out",
                quantity=Decimal("-100.00"),
                instrument_claim_refs=("claim-quote",),
                location_claim_ref="claim-location",
                subtype="quote",
                attributed_to_slot=None,
            ),
            ClaimLegSpec(
                slot=0,
                role="asset_in",
                quantity=Decimal("1.2500"),
                instrument_claim_refs=("claim-base",),
                location_claim_ref="claim-location",
                subtype="base",
                attributed_to_slot=None,
            ),
        ),
    )


def test_claim_stable_id_helpers_use_declared_recipes() -> None:
    claim_set_id = stable_claim_set_id(
        evidence_set_id="evidence-set-1",
        emitter_id="coinbase:coinbase:claim",
    )

    assert claim_set_id == "evidence-set-1:coinbase:coinbase:claim"
    assert (
        stable_claim_scope_id(
            claim_set_id=claim_set_id,
            scope_key=("member-1", "row:1"),
        )
        == "evidence-set-1:coinbase:coinbase:claim:member-1:row:1"
    )
    assert (
        stable_claim_bundle_id(
            scope_id="scope-1",
            key="default",
        )
        == "scope-1:default"
    )
    assert (
        stable_claim_id(
            bundle_id="bundle-1",
            kind=ClaimKind.ACTIVITY,
            key=("member-1", "row:1", "activity", "0"),
        )
        == "bundle-1:activity:member-1:row:1:activity:0"
    )
    assert stable_claim_bundle_decision_id(scope_id="scope-1") == "scope-1"


def test_claim_record_payload_preserves_decimal_temporal_precision_and_sorted_refs() -> (
    None
):
    payload = _activity_claim().to_payload()

    assert payload["member_refs"] == ["member-a", "member-b"]
    assert payload["observation_refs"] == ["observation-a", "observation-b"]
    assert payload["provenance_refs"] == ["prov-a", "prov-b"]
    assert payload["effective_at"] == "2026-03-23 12:00:00"
    assert payload["precision"] == TemporalPrecision.TIMESTAMP.value
    leg_specs = cast(list[dict[str, object]], payload["leg_specs"])
    assert isinstance(leg_specs, list)
    assert leg_specs[0]["quantity"] == "1.25"
    assert leg_specs[1]["quantity"] == "-100"


def test_claim_set_fingerprint_uses_canonical_ordering() -> None:
    first = ClaimSet(
        claim_set_id="claim-set-1",
        evidence_set_ref="working/products/evidence_sets/evidence-1/evidence_set.json",
        emitter_id="coinbase:coinbase:claim",
        claim_records=(
            ClaimRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-1",
                bundle_id="bundle-1",
                claim_id="claim-location",
                kind=ClaimKind.LOCATION,
                status=ClaimRecordStatus.ASSERTED,
                key=("scope-key", "location", "0"),
                member_refs=("member-1",),
                observation_refs=(),
                effective_at=None,
                precision=None,
                provenance_refs=(),
                location_ref="coinbase:primary",
                location_group_label="Coinbase",
                location_label="Primary",
            ),
            _activity_claim(),
        ),
        claim_bundle_records=(
            ClaimBundleRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-1",
                bundle_id="bundle-1",
                key="default",
                scope_key=("member-1", "row:1"),
                claim_refs=("claim-location", "claim-activity"),
            ),
        ),
        claim_bundle_decision_records=(
            ClaimBundleDecisionRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-1",
                decision_id="scope-1",
                outcome=ClaimBundleDecisionOutcome.ACCEPTED,
                accepted_bundle_ref="bundle-1",
                rejected_bundle_refs=(),
                deferred_bundle_refs=(),
                basis=ClaimBundleDecisionBasis.SINGLE_BUNDLE,
                blocking_gap_refs=(),
            ),
        ),
    )
    second = ClaimSet(
        claim_set_id=first.claim_set_id,
        evidence_set_ref=first.evidence_set_ref,
        emitter_id=first.emitter_id,
        claim_records=tuple(reversed(first.claim_records)),
        claim_bundle_records=first.claim_bundle_records,
        claim_bundle_decision_records=first.claim_bundle_decision_records,
    )

    assert claim_set_fingerprint(first) == claim_set_fingerprint(second)
    assert first.to_payload()["schema_version"] == CLAIM_SET_SCHEMA_VERSION


def test_claim_ordering_helpers_sort_canonically() -> None:
    activity = _activity_claim()
    location = ClaimRecord(
        claim_set_id="claim-set-1",
        scope_id="scope-1",
        bundle_id="bundle-1",
        claim_id="claim-location",
        kind=ClaimKind.LOCATION,
        status=ClaimRecordStatus.ASSERTED,
        key=("scope-key", "location", "0"),
        member_refs=("member-1",),
        observation_refs=(),
        effective_at=None,
        precision=None,
        provenance_refs=(),
        location_ref="coinbase:primary",
        location_group_label="Coinbase",
        location_label="Primary",
    )
    decisions = canonical_claim_bundle_decision_records(
        (
            ClaimBundleDecisionRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-2",
                decision_id="scope-2",
                outcome=ClaimBundleDecisionOutcome.BLOCKED,
                accepted_bundle_ref="",
                rejected_bundle_refs=(),
                deferred_bundle_refs=(),
                basis=ClaimBundleDecisionBasis.UPSTREAM_GAP,
                blocking_gap_refs=("gap-2", "gap-1"),
            ),
            ClaimBundleDecisionRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-1",
                decision_id="scope-1",
                outcome=ClaimBundleDecisionOutcome.ACCEPTED,
                accepted_bundle_ref="bundle-1",
                rejected_bundle_refs=(),
                deferred_bundle_refs=(),
                basis=ClaimBundleDecisionBasis.SINGLE_BUNDLE,
                blocking_gap_refs=(),
            ),
        )
    )

    assert tuple(
        record.claim_id for record in canonical_claim_records((activity, location))
    ) == (
        "claim-activity",
        "claim-location",
    )
    assert tuple(
        record.bundle_id
        for record in canonical_claim_bundle_records(
            (
                ClaimBundleRecord(
                    claim_set_id="claim-set-1",
                    scope_id="scope-2",
                    bundle_id="bundle-2",
                    key="default",
                    scope_key=("member-2", "row:2"),
                    claim_refs=("claim-2",),
                ),
                ClaimBundleRecord(
                    claim_set_id="claim-set-1",
                    scope_id="scope-1",
                    bundle_id="bundle-1",
                    key="default",
                    scope_key=("member-1", "row:1"),
                    claim_refs=("claim-1",),
                ),
            )
        )
    ) == ("bundle-1", "bundle-2")
    assert tuple(record.scope_id for record in decisions) == ("scope-1", "scope-2")


def test_claim_model_supports_zero_row_valuation_and_exact_decision_vocabulary() -> (
    None
):
    valuation = ClaimRecord(
        claim_set_id="claim-set-1",
        scope_id="scope-1",
        bundle_id="bundle-1",
        claim_id="claim-valuation",
        kind=ClaimKind.VALUATION,
        status=ClaimRecordStatus.SUPERSEDED,
        key=("scope-key", "valuation", "0"),
        member_refs=("member-1",),
        observation_refs=("observation-1",),
        effective_at=None,
        precision=TemporalPrecision.DATE,
        provenance_refs=(),
        purpose="statement_balance",
        amount=Decimal("2500.00"),
        currency="USD",
        valued_at=datetime(2026, 3, 23, tzinfo=UTC),
        location_claim_ref="claim-location",
        instrument_claim_refs=("claim-base",),
    )

    assert valuation.to_payload()["amount"] == "2500"
    assert valuation.to_payload()["valued_at"] == "2026-03-23"
    assert tuple(item.value for item in ClaimBundleDecisionOutcome) == (
        "accepted",
        "blocked",
        "deferred",
        "superseded",
    )


def test_claim_record_rejects_invalid_kind_owned_field_combinations() -> None:
    with pytest.raises(ValueError, match="activity claims must not set balance fields"):
        ClaimRecord(
            claim_set_id="claim-set-1",
            scope_id="scope-1",
            bundle_id="bundle-1",
            claim_id="claim-invalid",
            kind=ClaimKind.ACTIVITY,
            status=ClaimRecordStatus.ASSERTED,
            key=("scope-key", "activity", "0"),
            member_refs=("member-1",),
            observation_refs=(),
            effective_at=None,
            precision=None,
            provenance_refs=(),
            activity_label="buy",
            location_claim_ref="claim-location",
            leg_specs=(
                ClaimLegSpec(
                    slot=0,
                    role="asset_in",
                    quantity=Decimal("1"),
                    instrument_claim_refs=("claim-instrument",),
                    location_claim_ref="claim-location",
                    subtype="base",
                ),
            ),
            quantity=Decimal("1.00"),
            balance_kind="asset_balance",
            observed_at=datetime(2026, 3, 23, tzinfo=UTC),
        )
    with pytest.raises(
        ValueError,
        match="activity claims require activity_label, location_claim_ref, and leg_specs",
    ):
        ClaimRecord(
            claim_set_id="claim-set-1",
            scope_id="scope-1",
            bundle_id="bundle-1",
            claim_id="claim-activity",
            kind=ClaimKind.ACTIVITY,
            status=ClaimRecordStatus.ASSERTED,
            key=("scope-key", "activity", "0"),
            member_refs=("member-1",),
            observation_refs=(),
            effective_at=datetime(2026, 3, 23, tzinfo=UTC),
            precision=TemporalPrecision.TIMESTAMP,
            provenance_refs=(),
            activity_label="buy",
            location_claim_ref="",
            leg_specs=(),
        )
    with pytest.raises(
        ValueError,
        match="claim effective_at requires precision",
    ):
        ClaimRecord(
            claim_set_id="claim-set-1",
            scope_id="scope-1",
            bundle_id="bundle-1",
            claim_id="claim-activity",
            kind=ClaimKind.ACTIVITY,
            status=ClaimRecordStatus.ASSERTED,
            key=("scope-key", "activity", "0"),
            member_refs=("member-1",),
            observation_refs=(),
            effective_at=datetime(2026, 3, 23, tzinfo=UTC),
            precision=None,
            provenance_refs=(),
            activity_label="buy",
            location_claim_ref="claim-location",
            leg_specs=(
                ClaimLegSpec(
                    slot=0,
                    role="asset_in",
                    quantity=Decimal("1"),
                    instrument_claim_refs=("claim-instrument",),
                    location_claim_ref="claim-location",
                    subtype="base",
                ),
            ),
        )
    with pytest.raises(
        ValueError,
        match=(
            "valuation claims require purpose, amount, currency, valued_at, "
            "precision, location, and instruments"
        ),
    ):
        ClaimRecord(
            claim_set_id="claim-set-1",
            scope_id="scope-1",
            bundle_id="bundle-1",
            claim_id="claim-valuation",
            kind=ClaimKind.VALUATION,
            status=ClaimRecordStatus.ASSERTED,
            key=("scope-key", "valuation", "0"),
            member_refs=("member-1",),
            observation_refs=(),
            effective_at=None,
            precision=None,
            provenance_refs=(),
            purpose="statement_balance",
            amount=Decimal("100"),
            currency="USD",
            valued_at=datetime(2026, 3, 23, tzinfo=UTC),
            location_claim_ref="claim-location",
            instrument_claim_refs=("claim-instrument",),
        )
    with pytest.raises(
        ValueError,
        match=(
            "location claims require location_ref, location_group_label, and "
            "location_label"
        ),
    ):
        ClaimRecord(
            claim_set_id="claim-set-1",
            scope_id="scope-1",
            bundle_id="bundle-1",
            claim_id="claim-location",
            kind=ClaimKind.LOCATION,
            status=ClaimRecordStatus.ASSERTED,
            key=("scope-key", "location", "0"),
            member_refs=("member-1",),
            observation_refs=(),
            effective_at=None,
            precision=None,
            provenance_refs=(),
            location_ref="coinbase:primary",
            location_group_label="",
            location_label="Primary",
        )
