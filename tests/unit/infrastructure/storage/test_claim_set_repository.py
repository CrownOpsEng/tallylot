from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.domain.claim import (
    CLAIM_SET_SCHEMA_VERSION,
    ClaimBundleDecisionBasis,
    ClaimBundleDecisionOutcome,
    ClaimBundleDecisionRecord,
    ClaimBundleRecord,
    ClaimKind,
    ClaimRecord,
    ClaimRecordStatus,
    ClaimSet,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.infrastructure.storage import FilesystemClaimSetRepository


def _sample_claim_set() -> ClaimSet:
    return ClaimSet(
        claim_set_id="claim-set-1",
        evidence_set_ref="working/products/evidence_sets/evidence-set-1/evidence_set.json",
        emitter_id="coinbase:coinbase:claim",
        claim_records=(
            ClaimRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-1",
                bundle_id="bundle-1",
                claim_id="claim-1",
                kind=ClaimKind.BALANCE,
                status=ClaimRecordStatus.ASSERTED,
                key=("scope-key", "balance", "0"),
                member_refs=("member-1",),
                observation_refs=("observation-1",),
                effective_at=datetime(2026, 3, 23, tzinfo=UTC),
                precision=TemporalPrecision.DATE,
                provenance_refs=("prov-1",),
                location_claim_ref="claim-location",
                instrument_claim_refs=("claim-instrument",),
                balance_kind="asset_balance",
                quantity=Decimal("1.2500"),
                observed_at=datetime(2026, 3, 23, tzinfo=UTC),
            ),
        ),
        claim_bundle_records=(
            ClaimBundleRecord(
                claim_set_id="claim-set-1",
                scope_id="scope-1",
                bundle_id="bundle-1",
                key="default",
                scope_key=("member-1", "row:1"),
                claim_refs=("claim-1",),
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


def test_claim_set_repository_round_trips_json_payload(tmp_path: Path) -> None:
    repository = FilesystemClaimSetRepository()
    claim_set = _sample_claim_set()
    path = (
        tmp_path
        / "working"
        / "products"
        / "claim_sets"
        / "claim-set-1"
        / "claim_set.json"
    )

    repository.write_claim_set(path, claim_set)

    payload = json.loads(path.read_text(encoding="utf-8"))
    round_trip = repository.read_claim_set(path)

    assert payload["schema_version"] == CLAIM_SET_SCHEMA_VERSION
    assert round_trip == claim_set


def test_claim_set_repository_rejects_missing_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "claim_set.json"
    payload = _sample_claim_set().to_payload()
    payload.pop("schema_version")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported claim set schema_version: <missing>; expected "
            f"{CLAIM_SET_SCHEMA_VERSION}"
        ),
    ):
        FilesystemClaimSetRepository().read_claim_set(path)


def test_claim_set_repository_rejects_wrong_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "claim_set.json"
    payload = _sample_claim_set().to_payload()
    payload["schema_version"] = 999
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported claim set schema_version: 999; expected "
            f"{CLAIM_SET_SCHEMA_VERSION}"
        ),
    ):
        FilesystemClaimSetRepository().read_claim_set(path)


def test_claim_set_repository_rejects_non_object_payload(tmp_path: Path) -> None:
    path = tmp_path / "claim_set.json"
    path.write_text('["not", "an", "object"]', encoding="utf-8")

    with pytest.raises(ValueError, match="invalid claim set payload: expected object"):
        FilesystemClaimSetRepository().read_claim_set(path)


def test_claim_set_repository_rejects_malformed_record_arrays(tmp_path: Path) -> None:
    path = tmp_path / "claim_set.json"
    payload = _sample_claim_set().to_payload()
    payload["claim_records"] = {"not": "an array"}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError, match="invalid claim set claim_records: expected array"
    ):
        FilesystemClaimSetRepository().read_claim_set(path)
