"""Shared statement extraction result models."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence


@dataclass(frozen=True)
class PdfBalanceRows:
    adapter_id: str
    rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class StatementBalanceEvidenceBatch:
    balance_evidence: tuple[BalanceEvidence, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
