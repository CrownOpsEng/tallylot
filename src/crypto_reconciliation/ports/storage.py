"""Storage ports."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from crypto_reconciliation.domain.models import (
    CanonicalBalance,
    CanonicalEvent,
    IssueRecord,
    NormalizationReviewRecord,
)


class StoragePort(Protocol):
    def write_canonical_events(self, path: Path, events: tuple[CanonicalEvent, ...]) -> None:
        ...

    def write_canonical_balances(self, path: Path, balances: tuple[CanonicalBalance, ...]) -> None:
        ...

    def write_issue_records(self, path: Path, issues: tuple[IssueRecord, ...]) -> None:
        ...

    def write_review_records(
        self,
        path: Path,
        reviews: tuple[NormalizationReviewRecord, ...],
    ) -> None:
        ...
