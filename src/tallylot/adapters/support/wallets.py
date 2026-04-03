"""Shared wallet-evidence helpers for adapters."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.issues import IssueRecord
from tallylot.domain.wallet_identifiers import (
    BTC_ADDRESS_PATTERN,
    EVM_ADDRESS_PATTERN,
    SOLANA_ADDRESS_PATTERN,
    TRON_ADDRESS_PATTERN,
    normalized_identifier,
    wallet_identifier_kind,
)
from tallylot.ports.evidence import WalletInventoryRecord

__all__ = (
    "BTC_ADDRESS_PATTERN",
    "EVM_ADDRESS_PATTERN",
    "SOLANA_ADDRESS_PATTERN",
    "TRON_ADDRESS_PATTERN",
    "WalletIssueSpec",
    "WalletRecordSpec",
    "normalized_identifier",
    "wallet_identifier_kind",
    "wallet_issue",
    "wallet_record",
)


@dataclass(frozen=True)
class WalletRecordSpec:
    source: str
    identifier_kind: str
    identifier_value: str
    network_scope: str
    controller: str
    account_label: str
    evidence_kind: str
    evidence_path: str
    confidence: str
    note: str = ""


@dataclass(frozen=True)
class WalletIssueSpec:
    source: str
    adapter_id: str
    issue_kind: str
    message: str
    wallet_id: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""


def wallet_record(spec: WalletRecordSpec) -> WalletInventoryRecord:
    normalized = normalized_identifier(spec.identifier_kind, spec.identifier_value)
    return WalletInventoryRecord(
        source=spec.source,
        wallet_id=f"{spec.identifier_kind}:{normalized}",
        identifier_kind=spec.identifier_kind,
        identifier_value=spec.identifier_value,
        normalized_identifier=normalized,
        display_identifier=spec.identifier_value,
        network_scope=spec.network_scope,
        controller=spec.controller,
        account_label=spec.account_label,
        evidence_kind=spec.evidence_kind,
        evidence_path=spec.evidence_path,
        confidence=spec.confidence,
        notes=spec.note,
    )


def wallet_issue(spec: WalletIssueSpec) -> IssueRecord:
    issue_ref = spec.wallet_id or spec.raw_file or spec.issue_kind
    return IssueRecord(
        issue_id=f"{spec.adapter_id}:{spec.source}:{spec.issue_kind}:{issue_ref}",
        source=spec.source,
        adapter_id=spec.adapter_id,
        severity="medium",
        kind=spec.issue_kind,
        message=spec.message,
        raw_file=spec.raw_file,
        raw_row_ref=spec.raw_row_ref,
    )
