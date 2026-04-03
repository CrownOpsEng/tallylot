"""Typed evidence repository ports and records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tallylot.domain.checkpoints import BalanceEvidence, BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord


@dataclass(frozen=True)
class WalletInventoryRecord:
    source: str
    identifier_kind: str
    identifier_value: str
    wallet_id: str = ""
    account: str = ""
    wallet: str = ""
    capture_path: str = ""
    normalized_identifier: str = ""
    display_identifier: str = ""
    network_scope: str = ""
    controller: str = ""
    account_label: str = ""
    evidence_kind: str = ""
    evidence_path: str = ""
    confidence: str = ""
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "capture_path": self.capture_path,
            "wallet_id": self.wallet_id,
            "identifier_kind": self.identifier_kind,
            "normalized_identifier": self.normalized_identifier or self.identifier_value,
            "display_identifier": self.display_identifier or self.identifier_value,
            "network_scope": self.network_scope,
            "controller": self.controller,
            "account_label": self.account_label,
            "evidence_kind": self.evidence_kind,
            "evidence_path": self.evidence_path,
            "confidence": self.confidence,
            "account": self.account,
            "wallet": self.wallet,
            "identifier_value": self.identifier_value,
            "notes": self.notes,
        }


class EvidenceRepositoryPort(Protocol):
    def write_balance_snapshots(self, path: Path, balances: tuple[BalanceSnapshot, ...]) -> None: ...

    def write_balance_evidence(self, path: Path, evidence: tuple[BalanceEvidence, ...]) -> None: ...

    def write_issue_records(self, path: Path, issues: tuple[IssueRecord, ...]) -> None: ...

    def write_review_records(self, path: Path, reviews: tuple[NormalizationReviewRecord, ...]) -> None: ...

    def write_wallet_inventory(self, path: Path, wallet_inventory: tuple[WalletInventoryRecord, ...]) -> None: ...
