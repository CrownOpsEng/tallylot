"""Typed normalization workflow payloads."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import TransactionFact
from tallylot.ports.evidence import WalletInventoryRecord

from .annotations import FactAnnotationRecord


@dataclass(frozen=True)
class NormalizationOutputs:
    facts: tuple[TransactionFact, ...]
    fact_annotations: tuple[FactAnnotationRecord, ...]
    derived_balances: tuple[BalanceSnapshot, ...]
    balance_evidence: tuple[BalanceEvidence, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
    wallet_inventory: tuple[WalletInventoryRecord, ...]


@dataclass(frozen=True)
class NormalizationWindowStats:
    facts_outside_window: int
    issues_outside_window: int
