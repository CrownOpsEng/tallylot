"""ReconciliationState repository port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tallylot.domain.reconciliation import ReconciliationState


class ReconciliationStateRepositoryPort(Protocol):
    def read_reconciliation_state(self, path: Path) -> ReconciliationState: ...

    def write_reconciliation_state(
        self, path: Path, reconciliation_state: ReconciliationState
    ) -> None: ...
