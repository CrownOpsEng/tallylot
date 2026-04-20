"""EconomicFacts repository port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tallylot.domain.economics import EconomicFacts


class EconomicFactsRepositoryPort(Protocol):
    def read_economic_facts(self, path: Path) -> EconomicFacts: ...

    def write_economic_facts(
        self, path: Path, economic_facts: EconomicFacts
    ) -> None: ...
