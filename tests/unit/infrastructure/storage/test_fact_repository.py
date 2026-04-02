from __future__ import annotations

from pathlib import Path

from tallylot.domain.transactions import ProjectionType
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.storage import FilesystemFactRepository

FACT_HEADER = (
    "fact_id",
    "source",
    "adapter_id",
    "timestamp",
    "account",
    "wallet",
    "max_in_legs",
    "max_out_legs",
    "max_fee_legs",
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
    "fee_legs",
)


def _fact_row(*, projection_type: str) -> dict[str, str]:
    return {
        "fact_id": "fact-1",
        "source": "fixture",
        "adapter_id": "structured_csv",
        "timestamp": "2025-01-01 00:00:00",
        "account": "Taxable",
        "wallet": "Primary",
        "max_in_legs": "1",
        "max_out_legs": "1",
        "max_fee_legs": "1",
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
        "legs": "in:BTC:1::|out:CAD:100::",
        "fee_legs": "out:CAD:1::",
    }


def test_fact_repository_reads_machine_projection_values(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    write_rows(path, FACT_HEADER, (_fact_row(projection_type="trade"),))

    facts = FilesystemFactRepository().read_facts(path)

    assert facts[0].projection_type == ProjectionType.TRADE
    assert facts[0].leg_policy.max_fee_legs == 1
