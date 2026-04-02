from __future__ import annotations

from pathlib import Path

import pytest

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


def test_fact_repository_rejects_legacy_projection_labels(tmp_path: Path) -> None:
    path = tmp_path / "facts.csv"
    write_rows(path, FACT_HEADER, (_fact_row(projection_type="Trade"),))

    with pytest.raises(ValueError, match="Unsupported ProjectionType: Trade"):
        FilesystemFactRepository().read_facts(path)
