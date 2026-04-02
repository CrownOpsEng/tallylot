"""Storage ports."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from crypto_reconciliation.domain.models import (
    BalanceSnapshot,
    IssueRecord,
    NormalizationReviewRecord,
    NormalizedTransaction,
)


class StoragePort(Protocol):
    def write_transactions(self, path: Path, transactions: tuple[NormalizedTransaction, ...]) -> None: ...

    def write_balances(self, path: Path, balances: tuple[BalanceSnapshot, ...]) -> None: ...

    def write_issue_records(self, path: Path, issues: tuple[IssueRecord, ...]) -> None: ...

    def write_review_records(
        self,
        path: Path,
        reviews: tuple[NormalizationReviewRecord, ...],
    ) -> None: ...
