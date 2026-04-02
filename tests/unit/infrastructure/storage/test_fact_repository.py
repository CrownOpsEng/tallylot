from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    FACT_SCHEMA_VERSION,
    AccountingIntentHint,
    EconomicKind,
    EconomicLeg,
    FactLegPolicy,
    FactSemantics,
    LegKind,
    LegShapeLimit,
    ProjectionHint,
    TaxTreatmentHint,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, LocationId, SourceId, TransactionId
from tallylot.infrastructure.serialization.csv_io import read_rows, write_rows
from tallylot.infrastructure.storage import FilesystemFactRepository

FACT_HEADER = (
    "schema_version",
    "fact_id",
    "source",
    "adapter_id",
    "timestamp",
    "effective_at",
    "effective_precision",
    "location_id",
    "economic_kind",
    "projection_hint",
    "accounting_intent_hint",
    "tax_treatment_hint",
    "description",
    "provider_operation_key",
    "operation_group_id",
    "tx_hash",
    "raw_file",
    "raw_row_ref",
    "confidence",
    "status",
    "legs",
    "leg_policy",
)


def _fact_row(*, projection_hint: str) -> dict[str, str]:
    return {
        "schema_version": str(FACT_SCHEMA_VERSION),
        "fact_id": "fact-1",
        "source": "fixture",
        "adapter_id": "structured_csv",
        "timestamp": "2025-01-01 00:00:00",
        "effective_at": "",
        "effective_precision": "",
        "location_id": "taxable:primary",
        "economic_kind": "spot_trade",
        "projection_hint": projection_hint,
        "accounting_intent_hint": "asset_exchange",
        "tax_treatment_hint": "capital_exchange",
        "description": "fixture trade",
        "provider_operation_key": "trade",
        "operation_group_id": "",
        "tx_hash": "tx-1",
        "raw_file": "transactions.csv",
        "raw_row_ref": "2",
        "confidence": "high",
        "status": "mapped",
        "legs": (
            '[{"leg_id":"primary_btc","kind":"primary","subtype":"","instrument_id":"symbol:BTC","quantity":"1",'
            '"attributed_to_leg_id":"","location_id":""},'
            '{"leg_id":"primary_cad","kind":"primary","subtype":"","instrument_id":"symbol:CAD","quantity":"-100",'
            '"attributed_to_leg_id":"","location_id":""},'
            '{"leg_id":"fee_cad","kind":"charge","subtype":"","instrument_id":"symbol:CAD","quantity":"-1",'
            '"attributed_to_leg_id":"primary_cad","location_id":""}]'
        ),
        "leg_policy": (
            '[{"kind":"charge","min_count":0,"max_count":1,"min_positive_count":null,"max_positive_count":0,'
            '"min_negative_count":null,"max_negative_count":1},'
            '{"kind":"primary","min_count":0,"max_count":2,"min_positive_count":null,"max_positive_count":1,'
            '"min_negative_count":null,"max_negative_count":1}]'
        ),
    }


def test_fact_repository_reads_machine_projection_values(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    write_rows(path, FACT_HEADER, (_fact_row(projection_hint="trade"),))

    facts = FilesystemFactRepository().read_facts(path)

    assert facts[0].projection_hint == ProjectionHint.TRADE
    assert facts[0].leg_policy.limit_for(LegKind.CHARGE) is not None


def test_fact_repository_rejects_missing_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    row = _fact_row(projection_hint="trade")
    row["schema_version"] = ""
    write_rows(path, FACT_HEADER, (row,))

    try:
        FilesystemFactRepository().read_facts(path)
    except ValueError as error:
        assert str(error) == "unsupported fact schema_version: <missing>; expected 2"
    else:
        raise AssertionError("expected missing schema version to be rejected")


def test_fact_repository_rejects_effective_precision_without_effective_at(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    row = _fact_row(projection_hint="trade")
    row["effective_precision"] = "date"
    write_rows(path, FACT_HEADER, (row,))

    try:
        FilesystemFactRepository().read_facts(path)
    except ValueError as error:
        assert str(error) == "fact row effective_at and effective_precision must both be present or both be blank"
    else:
        raise AssertionError("expected orphaned effective_precision to be rejected")


def test_fact_repository_rejects_effective_at_without_effective_precision(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    row = _fact_row(projection_hint="trade")
    row["effective_at"] = "2025-01-02"
    write_rows(path, FACT_HEADER, (row,))

    try:
        FilesystemFactRepository().read_facts(path)
    except ValueError as error:
        assert str(error) == "fact row effective_at and effective_precision must both be present or both be blank"
    else:
        raise AssertionError("expected orphaned effective_at to be rejected")


def test_fact_repository_rejects_boolean_policy_counts(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    row = _fact_row(projection_hint="trade")
    row["leg_policy"] = (
        '[{"kind":"charge","min_count":0,"max_count":true,"min_positive_count":null,"max_positive_count":0,'
        '"min_negative_count":null,"max_negative_count":1},'
        '{"kind":"primary","min_count":0,"max_count":2,"min_positive_count":null,"max_positive_count":1,'
        '"min_negative_count":null,"max_negative_count":1}]'
    )
    write_rows(path, FACT_HEADER, (row,))

    try:
        FilesystemFactRepository().read_facts(path)
    except ValueError as error:
        assert str(error) == "missing required integer field: max_count"
    else:
        raise AssertionError("expected invalid boolean policy count to be rejected")


def test_fact_repository_round_trips_deterministic_legs_and_leg_policy(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    fact = TransactionFact(
        fact_id=TransactionId("fact-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        effective_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
        effective_precision=TemporalPrecision.DATE,
        location_id=LocationId("taxable:primary"),
        semantics=FactSemantics(
            economic_kind=EconomicKind.SPOT_TRADE,
            accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
            tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            projection_hint=ProjectionHint.TRADE,
        ),
        legs=(
            EconomicLeg(
                leg_id="primary_btc",
                kind=LegKind.PRIMARY,
                instrument_id=InstrumentId("symbol:BTC"),
                quantity=Decimal("1"),
            ),
            EconomicLeg(
                leg_id="primary_cad",
                kind=LegKind.PRIMARY,
                instrument_id=InstrumentId("symbol:CAD"),
                quantity=Decimal("-100"),
            ),
            EconomicLeg(
                leg_id="fee_cad",
                kind=LegKind.CHARGE,
                instrument_id=InstrumentId("symbol:CAD"),
                quantity=Decimal("-1"),
                subtype="trading_fee",
                attributed_to_leg_id="primary_cad",
            ),
        ),
        leg_policy=FactLegPolicy(
            limits=(
                LegShapeLimit(
                    kind=LegKind.PRIMARY,
                    min_count=2,
                    max_count=2,
                    min_positive_count=1,
                    max_positive_count=1,
                    min_negative_count=1,
                    max_negative_count=1,
                ),
                LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_positive_count=0, max_negative_count=1),
            )
        ),
        description="fixture trade",
        provider_operation_key="trade",
        tx_hash="tx-1",
        raw_file="transactions.csv",
        raw_row_ref="2",
    )

    FilesystemFactRepository().write_facts(path, (fact,))

    rows = read_rows(path)
    round_tripped = FilesystemFactRepository().read_facts(path)

    assert rows[0]["schema_version"] == "2"
    assert rows[0]["effective_at"] == "2025-01-02"
    assert rows[0]["effective_precision"] == "date"
    assert rows[0]["legs"] == (
        '[{"leg_id":"primary_btc","kind":"primary","subtype":"","instrument_id":"symbol:BTC","quantity":"1",'
        '"attributed_to_leg_id":"","location_id":""},'
        '{"leg_id":"primary_cad","kind":"primary","subtype":"","instrument_id":"symbol:CAD","quantity":"-100",'
        '"attributed_to_leg_id":"","location_id":""},'
        '{"leg_id":"fee_cad","kind":"charge","subtype":"trading_fee","instrument_id":"symbol:CAD","quantity":"-1",'
        '"attributed_to_leg_id":"primary_cad","location_id":""}]'
    )
    assert rows[0]["leg_policy"] == (
        '[{"kind":"charge","min_count":0,"max_count":1,"min_positive_count":null,"max_positive_count":0,'
        '"min_negative_count":null,"max_negative_count":1},'
        '{"kind":"primary","min_count":2,"max_count":2,"min_positive_count":1,"max_positive_count":1,'
        '"min_negative_count":1,"max_negative_count":1}]'
    )
    assert round_tripped[0].to_row() == fact.to_row()
