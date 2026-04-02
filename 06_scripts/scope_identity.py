#!/usr/bin/env python3

"""Shared scope-identity extraction and labeling helpers."""

from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

from wallet_inventory_common import infer_identifier_kind, normalize_identifier


EVM_ADDRESS = re.compile(r"0x[a-fA-F0-9]{40}")
XPUB_KEY = re.compile(r"\b(?:xpub|ypub|zpub|tpub|upub|vpub)[1-9A-HJ-NP-Za-km-z]{16,}\b")
NEAR_ACCOUNT = re.compile(r"\b[a-z0-9][a-z0-9_.-]{1,62}\.near\b")
NAMED_SCOPE = re.compile(r"(?:^|[/_. -])(account|wallet|address|uid|user[_ -]?id|account[_ -]?id)[_ -]*([a-zA-Z0-9]{3,})(?=$|[/_. -])", re.IGNORECASE)
GENERIC_SCOPE_IDENTIFIERS = {"capture", "export", "history", "incoming", "raw", "files", "report", "reports", "data", "state", "backup"}
SCOPE_HEADERS = ("address", "wallet", "account", "account id", "user id", "uid", "xpub", "public key")


def _clean_scalar(value: str) -> str:
    return " ".join(value.strip().split())


def _named_token(kind: str, value: str) -> str:
    normalized_kind = kind.lower().replace(" ", "_").replace("-", "_")
    normalized_value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return f"{normalized_kind}:{normalized_value}"


def extract_scope_tokens(text: str) -> set[str]:
    cleaned = _clean_scalar(text)
    if not cleaned:
        return set()
    tokens: set[str] = set()
    for match in EVM_ADDRESS.finditer(cleaned):
        tokens.add(f"evm:{match.group(0).lower()}")
    for match in XPUB_KEY.finditer(cleaned):
        tokens.add(f"xpub:{match.group(0)}")
    for match in NEAR_ACCOUNT.finditer(cleaned.lower()):
        tokens.add(f"near:{match.group(0)}")
    for scope_kind, identifier in NAMED_SCOPE.findall(cleaned):
        normalized_identifier = identifier.lower()
        if normalized_identifier in GENERIC_SCOPE_IDENTIFIERS:
            continue
        tokens.add(_named_token(scope_kind, normalized_identifier))
    if not tokens:
        kind = infer_identifier_kind(cleaned)
        normalized_identifier = normalize_identifier(kind, cleaned)
        if kind == "btc_address":
            tokens.add(f"btc:{normalized_identifier}")
        elif kind == "tron_address":
            tokens.add(f"tron:{normalized_identifier}")
        elif kind == "solana_address":
            tokens.add(f"solana:{normalized_identifier}")
        elif kind == "cardano_account_key":
            tokens.add(f"cardano:{normalized_identifier}")
    return tokens


def token_from_header_value(header: str, value: str) -> set[str]:
    normalized_header = _clean_scalar(header).lower()
    cleaned_value = _clean_scalar(value)
    if not cleaned_value:
        return set()
    tokens = extract_scope_tokens(cleaned_value)
    if tokens:
        return tokens
    if normalized_header in {"uid", "user id", "account id"}:
        compact = re.sub(r"[^a-zA-Z0-9]+", "", cleaned_value)
        if len(compact) >= 4:
            return {_named_token(normalized_header, compact)}
    return set()


def csv_scope_tokens(rows: Sequence[dict[str, str]]) -> frozenset[str]:
    tokens: set[str] = set()
    if not rows:
        return frozenset()
    headers = rows[0].keys()
    for header in headers:
        normalized_header = _clean_scalar(header).lower()
        if not any(normalized_header == candidate or normalized_header.endswith(f" {candidate}") for candidate in SCOPE_HEADERS):
            continue
        values = {_clean_scalar(row.get(header, "")) for row in rows if _clean_scalar(row.get(header, ""))}
        if len(values) != 1:
            continue
        value = next(iter(values))
        tokens.update(token_from_header_value(header, value))
    return frozenset(tokens)


def json_scope_tokens(payload: object) -> frozenset[str]:
    tokens: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                tokens.update(extract_scope_tokens(str(key)))
                walk(nested)
        elif isinstance(value, list):
            for item in value[:50]:
                walk(item)
        elif isinstance(value, str):
            tokens.update(extract_scope_tokens(value))

    walk(payload)
    return frozenset(tokens)


def content_scope_tokens(row: dict[str, str]) -> frozenset[str]:
    tokens: set[str] = set()
    for field in ("inspection_scope_tokens", "scope_tokens", "archive_scope_tokens"):
        value = row.get(field, "")
        if value:
            for part in value.split(";"):
                tokens.update(extract_scope_tokens(part))
    return frozenset(tokens)


def label_scope_tokens(row: dict[str, str], *, extra_fields: Iterable[str] = ()) -> frozenset[str]:
    fields = ("source_path", "archive_source_path", "bundle_id", *tuple(extra_fields))
    tokens: set[str] = set()
    for field in fields:
        value = row.get(field, "")
        if value:
            for part in value.split(";"):
                tokens.update(extract_scope_tokens(part))
    return frozenset(tokens)


def row_scope_tokens(row: dict[str, str], *, extra_fields: Iterable[str] = ()) -> frozenset[str]:
    content_tokens = content_scope_tokens(row)
    if content_tokens:
        return content_tokens
    return label_scope_tokens(row, extra_fields=extra_fields)


def inventory_scope_labels(repo_root: Path) -> dict[str, str]:
    wallet_inventory = repo_root / "03_analysis" / "inventory" / "wallet_inventory.csv"
    if not wallet_inventory.exists():
        return {}
    labels: dict[str, str] = {}
    with wallet_inventory.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            identifier_kind = (row.get("identifier_kind") or "").strip()
            normalized_identifier = (row.get("normalized_identifier") or "").strip()
            if not identifier_kind or not normalized_identifier:
                continue
            token = ""
            if identifier_kind == "evm_address":
                token = f"evm:{normalized_identifier.lower()}"
            elif identifier_kind == "btc_xpub":
                token = f"xpub:{normalized_identifier}"
            elif identifier_kind == "near_account":
                token = f"near:{normalized_identifier.lower()}"
            elif identifier_kind == "btc_address":
                token = f"btc:{normalized_identifier.lower()}"
            elif identifier_kind == "tron_address":
                token = f"tron:{normalized_identifier}"
            elif identifier_kind == "solana_address":
                token = f"solana:{normalized_identifier}"
            elif identifier_kind == "cardano_account_key":
                token = f"cardano:{normalized_identifier}"
            if not token:
                continue
            display = (row.get("display_identifier") or normalized_identifier).strip()
            account_labels = (row.get("account_labels") or "").strip()
            source_labels = (row.get("source_labels") or "").strip()
            label_parts = [display]
            if account_labels:
                label_parts.append(account_labels)
            elif source_labels:
                label_parts.append(source_labels)
            labels[token] = " / ".join(label_parts)
    return labels


@lru_cache(maxsize=8)
def _cached_inventory_scope_labels(repo_root: str) -> dict[str, str]:
    return inventory_scope_labels(Path(repo_root))


def describe_scope_tokens(tokens: Iterable[str], repo_root: Path | None = None) -> str:
    unique = sorted(set(tokens))
    if not unique:
        return ""
    labels = _cached_inventory_scope_labels(str(repo_root.resolve())) if repo_root is not None else {}
    rendered = [labels.get(token, token) for token in unique]
    return "; ".join(rendered)
