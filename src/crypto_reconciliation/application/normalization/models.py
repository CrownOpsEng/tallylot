"""Typed normalization workflow payloads."""

from __future__ import annotations

from dataclasses import dataclass

from crypto_reconciliation.domain.checkpoints import BalanceEvidence, BalanceSnapshot
from crypto_reconciliation.domain.issues import IssueRecord, NormalizationReviewRecord
from crypto_reconciliation.domain.transactions import TransactionFact
from crypto_reconciliation.ports.evidence import WalletInventoryRecord


@dataclass(frozen=True)
class NormalizationOutputs:
    facts: tuple[TransactionFact, ...]
    derived_balances: tuple[BalanceSnapshot, ...]
    balance_evidence: tuple[BalanceEvidence, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
    wallet_inventory: tuple[WalletInventoryRecord, ...]


@dataclass(frozen=True)
class NormalizationWindowStats:
    facts_outside_window: int
    issues_outside_window: int
