"""Typed normalization workflow payloads."""

from __future__ import annotations

from dataclasses import dataclass

from crypto_reconciliation.domain.models import (
    BalanceEvidence,
    BalanceSnapshot,
    IssueRecord,
    NormalizationReviewRecord,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.models.transactions import NormalizedTransaction


@dataclass(frozen=True)
class NormalizationOutputs:
    transactions: tuple[NormalizedTransaction, ...]
    derived_balances: tuple[BalanceSnapshot, ...]
    balance_evidence: tuple[BalanceEvidence, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
    wallet_inventory: tuple[WalletInventoryRecord, ...]


@dataclass(frozen=True)
class NormalizationWindowStats:
    transactions_outside_window: int
    issues_outside_window: int
