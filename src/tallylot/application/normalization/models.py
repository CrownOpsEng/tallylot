"""Typed normalization workflow payloads."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import TransactionFact
from tallylot.ports.evidence import LocationInventoryRecord

from .annotations import FactAnnotationRecord, LocationAnnotationRecord


@dataclass(frozen=True)
class NormalizationOutputs:
    facts: tuple[TransactionFact, ...]
    fact_annotations: tuple[FactAnnotationRecord, ...]
    location_annotations: tuple[LocationAnnotationRecord, ...]
    derived_balances: tuple[BalanceSnapshot, ...]
    balance_evidence: tuple[BalanceEvidence, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
    location_inventory: tuple[LocationInventoryRecord, ...]


@dataclass(frozen=True)
class NormalizationWindowStats:
    facts_outside_window: int
    issues_outside_window: int
    reviews_outside_window: int
