"""EvidenceSet repository port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tallylot.domain.evidence import EvidenceSet


class EvidenceSetRepositoryPort(Protocol):
    def read_evidence_set(self, path: Path) -> EvidenceSet: ...

    def write_evidence_set(self, path: Path, evidence_set: EvidenceSet) -> None: ...
