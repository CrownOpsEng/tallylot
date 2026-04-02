"""Shared wallet-identifier support for source adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass

from crypto_reconciliation.domain.models import IssueRecord, WalletInventoryRecord

EVM_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
BTC_XPUB_PATTERN = re.compile(r"xpub[1-9A-HJ-NP-Za-km-z]+")
TRON_ADDRESS_PATTERN = re.compile(r"T[1-9A-HJ-NP-Za-km-z]{33}")
BTC_ADDRESS_PATTERN = re.compile(r"(bc1[ac-hj-np-z02-9]{11,71}|[13][1-9A-HJ-NP-Za-km-z]{25,34})")
SOLANA_ADDRESS_PATTERN = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")

_IDENTIFIER_PATTERNS = (
    ("btc_xpub", BTC_XPUB_PATTERN),
    ("evm_address", EVM_ADDRESS_PATTERN),
    ("tron_address", TRON_ADDRESS_PATTERN),
    ("btc_address", BTC_ADDRESS_PATTERN),
    ("solana_address", SOLANA_ADDRESS_PATTERN),
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
class AdapterIssueSpec:
    source: str
    adapter_id: str
    issue_kind: str
    message: str
    wallet_id: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""


def normalized_identifier(identifier_kind: str, identifier_value: str) -> str:
    normalized = identifier_value.strip()
    if identifier_kind in {"evm_address", "address_alias"}:
        return normalized.lower()
    return normalized


def wallet_identifier_kind(identifier_value: str) -> str:
    value = identifier_value.strip()
    for identifier_kind, pattern in _IDENTIFIER_PATTERNS:
        if pattern.fullmatch(value):
            return identifier_kind
    if re.fullmatch(r"[a-fA-F0-9]{64,}", value):
        return "cardano_account_key"
    if re.fullmatch(r"[a-z0-9_.-]{6,64}", value):
        return "near_account"
    return "unknown"


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


def adapter_issue(spec: AdapterIssueSpec) -> IssueRecord:
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
