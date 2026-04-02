#!/usr/bin/env python3

"""Shared wallet-inventory row helpers used by adapters and inventory scripts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence


WALLET_EVIDENCE_HEADERS = (
    "source",
    "capture_path",
    "wallet_id",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scope",
    "controller",
    "account_label",
    "evidence_kind",
    "evidence_path",
    "confidence",
    "note",
)

WALLET_ISSUE_HEADERS = (
    "source",
    "capture_path",
    "wallet_id",
    "issue_kind",
    "message",
    "evidence_path",
)

EVM_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
NEAR_HEX_ACCOUNT_PATTERN = re.compile(r"(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])")
BTC_XPUB_PATTERN = re.compile(r"^(?:xpub|ypub|zpub|tpub|upub|vpub)[1-9A-HJ-NP-Za-km-z]+$")
BTC_ADDRESS_PATTERN = re.compile(r"^(?:bc1[ac-hj-np-z02-9]{11,87}|[13][1-9A-HJ-NP-Za-km-z]{25,34})$")
TRON_ADDRESS_PATTERN = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
SOLANA_ADDRESS_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def infer_identifier_kind(value: str) -> str:
    text = value.strip()
    lower = text.lower()
    if lower.endswith(".near"):
        return "near_account"
    if EVM_ADDRESS_PATTERN.fullmatch(text):
        return "evm_address"
    if BTC_XPUB_PATTERN.fullmatch(text):
        return "btc_xpub"
    if BTC_ADDRESS_PATTERN.fullmatch(lower):
        return "btc_address"
    if TRON_ADDRESS_PATTERN.fullmatch(text):
        return "tron_address"
    if SOLANA_ADDRESS_PATTERN.fullmatch(text):
        return "solana_address"
    if lower.startswith("addr1") or len(text) >= 80 and all(char in "0123456789abcdef" for char in lower):
        return "cardano_account_key"
    if NEAR_HEX_ACCOUNT_PATTERN.fullmatch(lower):
        return "near_account"
    return "address_alias"


def normalize_identifier(identifier_kind: str, value: str) -> str:
    text = value.strip()
    if identifier_kind in {"evm_address", "near_account", "address_alias", "btc_address"}:
        return text.lower()
    return text


def wallet_id_for(identifier_kind: str, normalized_identifier: str) -> str:
    return f"{identifier_kind}:{normalized_identifier}"


def wallet_evidence_row(
    *,
    source: str,
    raw_dir: Path,
    identifier_value: str,
    network_scope: str,
    controller: str,
    account_label: str,
    evidence_kind: str,
    evidence_path: Path,
    confidence: str,
    note: str = "",
    identifier_kind: str | None = None,
) -> dict[str, str]:
    kind = identifier_kind or infer_identifier_kind(identifier_value)
    normalized_identifier = normalize_identifier(kind, identifier_value)
    return {
        "source": source,
        "capture_path": str(raw_dir),
        "wallet_id": wallet_id_for(kind, normalized_identifier),
        "identifier_kind": kind,
        "normalized_identifier": normalized_identifier,
        "display_identifier": identifier_value.strip(),
        "network_scope": network_scope.strip(),
        "controller": controller,
        "account_label": account_label.strip(),
        "evidence_kind": evidence_kind,
        "evidence_path": str(evidence_path),
        "confidence": confidence,
        "note": note.strip(),
    }


def wallet_issue_row(
    *,
    source: str,
    raw_dir: Path,
    wallet_id: str,
    issue_kind: str,
    message: str,
    evidence_path: Path | None = None,
) -> dict[str, str]:
    return {
        "source": source,
        "capture_path": str(raw_dir),
        "wallet_id": wallet_id,
        "issue_kind": issue_kind,
        "message": message,
        "evidence_path": str(evidence_path) if evidence_path is not None else "",
    }


def dedupe_rows(rows: Iterable[dict[str, str]], *, key_fields: Sequence[str]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        key = tuple(row.get(field, "") for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
