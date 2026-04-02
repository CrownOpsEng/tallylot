from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.domain.transactions import (
    EconomicKind,
    EconomicLeg,
    FactClassification,
    FactLegPolicy,
    JournalIntent,
    LegKind,
    LegShapeLimit,
    ProjectionType,
    TaxTreatmentCode,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from tallylot.infrastructure.serialization.csv_io import read_rows, write_rows
from tallylot.infrastructure.storage import FilesystemFactRepository

FACT_HEADER = (
    "fact_id",
    "source",
    "adapter_id",
    "timestamp",
    "account",
    "wallet",
    "economic_kind",
    "projection_type",
    "journal_intent",
    "tax_treatment_code",
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


def _fact_row(*, projection_type: str) -> dict[str, str]:
    return {
        "fact_id": "fact-1",
        "source": "fixture",
        "adapter_id": "structured_csv",
        "timestamp": "2025-01-01 00:00:00",
        "account": "Taxable",
        "wallet": "Primary",
        "economic_kind": "spot_trade",
        "projection_type": projection_type,
        "journal_intent": "asset_exchange",
        "tax_treatment_code": "capital_exchange",
        "description": "fixture trade",
        "provider_operation_key": "trade",
        "operation_group_id": "",
        "tx_hash": "tx-1",
        "raw_file": "transactions.csv",
        "raw_row_ref": "2",
        "confidence": "high",
        "status": "mapped",
        "legs": (
            '[{"direction":"in","kind":"primary","subtype":"","asset":"BTC","amount":"1",'
            '"attributed_to_direction":"","account":"","wallet":""},'
            '{"direction":"out","kind":"primary","subtype":"","asset":"CAD","amount":"100",'
            '"attributed_to_direction":"","account":"","wallet":""},'
            '{"direction":"out","kind":"charge","subtype":"","asset":"CAD","amount":"1",'
            '"attributed_to_direction":"out","account":"","wallet":""}]'
        ),
        "leg_policy": (
            '[{"kind":"charge","min_count":0,"max_count":1,"min_in_count":null,"max_in_count":0,'
            '"min_out_count":null,"max_out_count":1},'
            '{"kind":"primary","min_count":0,"max_count":2,"min_in_count":null,"max_in_count":1,'
            '"min_out_count":null,"max_out_count":1}]'
        ),
    }


def test_fact_repository_reads_machine_projection_values(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    write_rows(path, FACT_HEADER, (_fact_row(projection_type="trade"),))

    facts = FilesystemFactRepository().read_facts(path)

    assert facts[0].projection_type == ProjectionType.TRADE
    assert facts[0].leg_policy.limit_for(LegKind.CHARGE) is not None


def test_fact_repository_rejects_boolean_policy_counts(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    row = _fact_row(projection_type="trade")
    row["leg_policy"] = (
        '[{"kind":"charge","min_count":0,"max_count":true,"min_in_count":null,"max_in_count":0,'
        '"min_out_count":null,"max_out_count":1},'
        '{"kind":"primary","min_count":0,"max_count":2,"min_in_count":null,"max_in_count":1,'
        '"min_out_count":null,"max_out_count":1}]'
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
        account="Taxable",
        wallet="Primary",
        classification=FactClassification(
            economic_kind=EconomicKind.SPOT_TRADE,
            journal_intent=JournalIntent.ASSET_EXCHANGE,
            tax_treatment_code=TaxTreatmentCode.CAPITAL_EXCHANGE,
            projection_type=ProjectionType.TRADE,
        ),
        legs=(
            EconomicLeg(direction="in", kind=LegKind.PRIMARY, asset=AssetSymbol("BTC"), amount=Decimal("1")),
            EconomicLeg(direction="out", kind=LegKind.PRIMARY, asset=AssetSymbol("CAD"), amount=Decimal("100")),
            EconomicLeg(
                direction="out",
                kind=LegKind.CHARGE,
                asset=AssetSymbol("CAD"),
                amount=Decimal("1"),
                subtype="trading_fee",
                attributed_to_direction="out",
            ),
        ),
        leg_policy=FactLegPolicy(
            limits=(
                LegShapeLimit(
                    kind=LegKind.PRIMARY,
                    min_count=2,
                    max_count=2,
                    min_in_count=1,
                    max_in_count=1,
                    min_out_count=1,
                    max_out_count=1,
                ),
                LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
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

    assert rows[0]["legs"] == (
        '[{"direction":"in","kind":"primary","subtype":"","asset":"BTC","amount":"1",'
        '"attributed_to_direction":"","account":"","wallet":""},'
        '{"direction":"out","kind":"primary","subtype":"","asset":"CAD","amount":"100",'
        '"attributed_to_direction":"","account":"","wallet":""},'
        '{"direction":"out","kind":"charge","subtype":"trading_fee","asset":"CAD","amount":"1",'
        '"attributed_to_direction":"out","account":"","wallet":""}]'
    )
    assert rows[0]["leg_policy"] == (
        '[{"kind":"charge","min_count":0,"max_count":1,"min_in_count":null,"max_in_count":0,'
        '"min_out_count":null,"max_out_count":1},'
        '{"kind":"primary","min_count":2,"max_count":2,"min_in_count":1,"max_in_count":1,'
        '"min_out_count":1,"max_out_count":1}]'
    )
    assert round_tripped[0].to_row() == fact.to_row()
