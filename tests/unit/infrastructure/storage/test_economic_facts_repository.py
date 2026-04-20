from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.domain.economics import (
    ECONOMIC_FACTS_SCHEMA_VERSION,
    EconomicEventKind,
    EconomicEventRecord,
    EconomicFacts,
    EconomicLegRecord,
    EconomicLegRole,
    LifecycleEvent,
    SettlementStatus,
)
from tallylot.infrastructure.storage import FilesystemEconomicFactsRepository


def _sample_economic_facts() -> EconomicFacts:
    return EconomicFacts(
        economic_facts_id='["claim-set-ref"]',
        claim_set_refs=("claim-set-ref",),
        economic_event_records=(
            EconomicEventRecord(
                event_id='["bundle-1",0]',
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
                leg_id='["event-1","holding_change",["position",[["owner:1"],["location:1"],["instrument:1"],null,"held_position"]],0]',
                event_id='["bundle-1",0]',
                role=EconomicLegRole.HOLDING_CHANGE,
                subject_ref=(
                    "position",
                    (
                        ("owner:1",),
                        ("location:1",),
                        ("instrument:1",),
                        None,
                        "held_position",
                    ),
                ),
                instrument_ref=("instrument:1",),
                location_ref=("location:1",),
                quantity=Decimal("1.25"),
            ),
        ),
        valuation_records=(),
    )


def test_economic_facts_repository_round_trips_json_payload(tmp_path: Path) -> None:
    repository = FilesystemEconomicFactsRepository()
    economic_facts = _sample_economic_facts()
    path = (
        tmp_path
        / "working"
        / "products"
        / "economic_facts"
        / "facts-1"
        / "economic_facts.json"
    )

    repository.write_economic_facts(path, economic_facts)

    payload = json.loads(path.read_text(encoding="utf-8"))
    round_trip = repository.read_economic_facts(path)

    assert payload["schema_version"] == ECONOMIC_FACTS_SCHEMA_VERSION
    assert payload["valuation_records"] == []
    assert round_trip == economic_facts


def test_economic_facts_repository_rejects_missing_schema_version(
    tmp_path: Path,
) -> None:
    path = tmp_path / "economic_facts.json"
    payload = _sample_economic_facts().to_payload()
    payload.pop("schema_version")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported economic facts schema_version: <missing>; expected "
            f"{ECONOMIC_FACTS_SCHEMA_VERSION}"
        ),
    ):
        FilesystemEconomicFactsRepository().read_economic_facts(path)


def test_economic_facts_repository_rejects_wrong_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "economic_facts.json"
    payload = _sample_economic_facts().to_payload()
    payload["schema_version"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported economic facts schema_version: 99; expected "
            f"{ECONOMIC_FACTS_SCHEMA_VERSION}"
        ),
    ):
        FilesystemEconomicFactsRepository().read_economic_facts(path)
