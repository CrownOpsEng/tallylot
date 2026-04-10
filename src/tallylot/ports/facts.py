"""Typed fact repository ports."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tallylot.domain.transactions import TransactionFact

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


class FactRepositoryPort(Protocol):
    def read_facts(self, path: Path) -> tuple[TransactionFact, ...]: ...

    def write_facts(self, path: Path, facts: tuple[TransactionFact, ...]) -> None: ...
