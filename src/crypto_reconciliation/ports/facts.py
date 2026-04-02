"""Typed fact repository ports."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from crypto_reconciliation.domain.transactions import TransactionFact


class FactRepositoryPort(Protocol):
    def read_facts(self, path: Path) -> tuple[TransactionFact, ...]: ...

    def write_facts(self, path: Path, facts: tuple[TransactionFact, ...]) -> None: ...
