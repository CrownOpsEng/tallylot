"""ClaimSet repository port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tallylot.domain.claim import ClaimSet


class ClaimSetRepositoryPort(Protocol):
    def read_claim_set(self, path: Path) -> ClaimSet: ...

    def write_claim_set(self, path: Path, claim_set: ClaimSet) -> None: ...
