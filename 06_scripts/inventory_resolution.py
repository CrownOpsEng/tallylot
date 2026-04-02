#!/usr/bin/env python3

"""Inventory-backed source resolution for intake routing."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from pipeline_common import source_slug
from scope_identity import describe_scope_tokens


ETH_BOUNDARY = re.compile(r"(?<![a-z0-9])eth(?![a-z0-9])")
BTC_BOUNDARY = re.compile(r"(?<![a-z0-9])btc(?![a-z0-9])")
ADA_BOUNDARY = re.compile(r"(?<![a-z0-9])ada(?![a-z0-9])")
TRX_BOUNDARY = re.compile(r"(?<![a-z0-9])trx(?![a-z0-9])")
SOL_BOUNDARY = re.compile(r"(?<![a-z0-9])sol(?![a-z0-9])")


@dataclass(frozen=True)
class InventoryRouteResolution:
    source_label: str
    source_folder: str
    confidence: str
    review_codes: tuple[str, ...]
    review_reason: str
    match_status: str
    suggested_source_label: str
    suggested_source_folder: str


def _read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    if not path.exists():
        return ()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


@lru_cache(maxsize=8)
def _wallet_inventory_evidence_rows(repo_root: str) -> tuple[dict[str, str], ...]:
    return _read_csv_rows(Path(repo_root) / "03_analysis" / "inventory" / "wallet_inventory_evidence.csv")


@lru_cache(maxsize=8)
def _source_inventory_rows(repo_root: str) -> tuple[dict[str, str], ...]:
    return _read_csv_rows(Path(repo_root) / "03_analysis" / "issues" / "source_inventory.csv")


def _source_folder_from_capture_path(capture_path: str) -> str:
    parts = Path(capture_path).parts
    if len(parts) >= 3 and parts[:3] == ("01_raw_exports", "external", parts[2]):
        return parts[2]
    if len(parts) >= 2 and parts[0] == "01_raw_exports":
        return parts[1]
    return ""


@lru_cache(maxsize=8)
def _source_inventory_by_slug(repo_root: str) -> dict[str, dict[str, str]]:
    rows = _source_inventory_rows(repo_root)
    results: dict[str, dict[str, str]] = {}
    for row in rows:
        source = (row.get("source") or "").strip()
        capture_path = (row.get("capture_path") or "").strip()
        if not source or not capture_path:
            continue
        results[source_slug(source)] = {
            "source": source,
            "source_folder": _source_folder_from_capture_path(capture_path) or source_slug(source),
            "capture_path": capture_path,
        }
    return results


def _split_tokens(value: str) -> frozenset[str]:
    return frozenset(part.strip() for part in value.split(";") if part.strip())


def _token_to_wallet_id(token: str) -> str:
    if token.startswith("evm:"):
        return f"evm_address:{token.removeprefix('evm:')}"
    if token.startswith("xpub:"):
        return f"btc_xpub:{token.removeprefix('xpub:')}"
    if token.startswith("near:"):
        return f"near_account:{token.removeprefix('near:')}"
    if token.startswith("btc:"):
        return f"btc_address:{token.removeprefix('btc:')}"
    if token.startswith("tron:"):
        return f"tron_address:{token.removeprefix('tron:')}"
    if token.startswith("solana:"):
        return f"solana_address:{token.removeprefix('solana:')}"
    if token.startswith("cardano:"):
        return f"cardano_account_key:{token.removeprefix('cardano:')}"
    return ""


def infer_network_hints(relative_path: Path, inspection_row: dict[str, str]) -> frozenset[str]:
    text = " / ".join(
        part
        for part in (
            *relative_path.parts,
            inspection_row.get("family", ""),
            inspection_row.get("header_preview", ""),
        )
        if part
    ).lower()
    hints: set[str] = set()
    if "polygon" in text or "matic" in text:
        hints.add("polygon")
    if "bsc" in text or "binance smart chain" in text:
        hints.add("bsc")
    if "ethereum" in text or ETH_BOUNDARY.search(text):
        hints.add("ethereum")
    if "near" in text:
        hints.add("near")
    if "bitcoin" in text or BTC_BOUNDARY.search(text) or "xpub" in text:
        hints.add("bitcoin")
    if "cardano" in text or ADA_BOUNDARY.search(text):
        hints.add("cardano")
    if "tron" in text or TRX_BOUNDARY.search(text):
        hints.add("tron")
    if "solana" in text or SOL_BOUNDARY.search(text):
        hints.add("solana")
    return frozenset(hints)


def _generic_network_name(network: str) -> str:
    return {
        "bsc": "BSC",
        "ethereum": "Ethereum",
        "polygon": "Polygon",
        "near": "NEAR",
        "bitcoin": "Bitcoin",
        "cardano": "Cardano",
        "tron": "TRON",
        "solana": "Solana",
    }.get(network, network.title())


def _short_scope_fragment(token: str) -> str:
    value = token.split(":", 1)[1] if ":" in token else token
    if value.startswith("0x") and len(value) >= 10:
        return value[:10]
    return value[:12]


def _generic_unknown_resolution(scope_tokens: frozenset[str], network_hints: frozenset[str]) -> InventoryRouteResolution:
    preferred_token = sorted(scope_tokens)[0] if len(scope_tokens) == 1 else ""
    preferred_network = sorted(network_hints)[0] if len(network_hints) == 1 else ""
    if preferred_network and preferred_token:
        fragment = _short_scope_fragment(preferred_token)
        source_label = f"{_generic_network_name(preferred_network)} Wallet {fragment}"
        source_folder = f"{source_slug(preferred_network)}-wallet-{source_slug(fragment)}"
        return InventoryRouteResolution(
            source_label=source_label,
            source_folder=source_folder,
            confidence="high",
            review_codes=(),
            review_reason="",
            match_status="generic_scope_routing",
            suggested_source_label="",
            suggested_source_folder="",
        )
    if preferred_network:
        source_label = f"{_generic_network_name(preferred_network)} Wallet"
        source_folder = f"{source_slug(preferred_network)}-wallet-unassigned"
        return InventoryRouteResolution(
            source_label=source_label,
            source_folder=source_folder,
            confidence="medium",
            review_codes=("inventory_match_ambiguous",),
            review_reason=f"Could not isolate one wallet scope inside {_generic_network_name(preferred_network)} export.",
            match_status="generic_network_review",
            suggested_source_label="",
            suggested_source_folder="",
        )
    return InventoryRouteResolution(
        source_label="Wallet Export",
        source_folder="wallet-export-unassigned",
        confidence="low",
        review_codes=("inventory_match_missing",),
        review_reason="Could not match wallet export to inventory or isolate one network scope.",
        match_status="generic_unresolved_review",
        suggested_source_label="",
        suggested_source_folder="",
    )


def _candidate_rows(
    repo_root: Path,
    *,
    scope_tokens: frozenset[str],
) -> list[dict[str, str]]:
    if not scope_tokens:
        return []
    wallet_ids = {wallet_id for token in scope_tokens if (wallet_id := _token_to_wallet_id(token))}
    if not wallet_ids:
        return []
    rows = [row for row in _wallet_inventory_evidence_rows(str(repo_root.resolve())) if (row.get("wallet_id") or "").strip() in wallet_ids]
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        key = (
            (row.get("source") or "").strip(),
            (row.get("network_scope") or "").strip(),
            (row.get("account_label") or "").strip(),
            (row.get("wallet_id") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _candidate_summary(rows: Iterable[dict[str, str]]) -> str:
    rendered: list[str] = []
    seen: set[str] = set()
    for row in rows:
        source = (row.get("source") or "").strip()
        network = (row.get("network_scope") or "").strip()
        account_label = (row.get("account_label") or "").strip()
        parts = [source]
        if network:
            parts.append(network)
        if account_label:
            parts.append(account_label)
        label = " / ".join(part for part in parts if part)
        if label and label not in seen:
            seen.add(label)
            rendered.append(label)
    return "; ".join(rendered)


def resolve_inventory_route(
    *,
    repo_root: Path,
    relative_path: Path,
    inspection_row: dict[str, str],
    default_source_label: str,
    default_source_folder: str,
    generic_wallet_routing: bool,
) -> InventoryRouteResolution:
    scope_tokens = _split_tokens(inspection_row.get("scope_tokens", ""))
    network_hints = infer_network_hints(relative_path, inspection_row)

    if generic_wallet_routing:
        candidates = _candidate_rows(repo_root, scope_tokens=scope_tokens)
        distinct_sources = sorted({(row.get("source") or "").strip() for row in candidates if (row.get("source") or "").strip()})
        if len(distinct_sources) == 1:
            source_slug_key = source_slug(distinct_sources[0])
            source_inventory = _source_inventory_by_slug(str(repo_root.resolve())).get(source_slug_key)
            source_label = source_inventory["source"] if source_inventory is not None else distinct_sources[0]
            source_folder = source_inventory["source_folder"] if source_inventory is not None else source_slug(distinct_sources[0])
            return InventoryRouteResolution(
                source_label=source_label,
                source_folder=source_folder,
                confidence="high",
                review_codes=(),
                review_reason="",
                match_status="inventory_source_match",
                suggested_source_label="",
                suggested_source_folder="",
            )
        if len(distinct_sources) > 1 and network_hints:
            filtered = [row for row in candidates if not row.get("network_scope") or row.get("network_scope") in network_hints]
            filtered_sources = sorted({(row.get("source") or "").strip() for row in filtered if (row.get("source") or "").strip()})
            if len(filtered_sources) == 1:
                source_slug_key = source_slug(filtered_sources[0])
                source_inventory = _source_inventory_by_slug(str(repo_root.resolve())).get(source_slug_key)
                source_label = source_inventory["source"] if source_inventory is not None else filtered_sources[0]
                source_folder = source_inventory["source_folder"] if source_inventory is not None else source_slug(filtered_sources[0])
                return InventoryRouteResolution(
                    source_label=source_label,
                    source_folder=source_folder,
                    confidence="high",
                    review_codes=(),
                    review_reason="",
                    match_status="inventory_source_match",
                    suggested_source_label="",
                    suggested_source_folder="",
                )
            if filtered_sources:
                candidates = filtered
                distinct_sources = filtered_sources
        if len(distinct_sources) > 1:
            generic = _generic_unknown_resolution(scope_tokens, network_hints)
            summary = _candidate_summary(candidates)
            token_preview = describe_scope_tokens(scope_tokens, repo_root)
            return InventoryRouteResolution(
                source_label=generic.source_label,
                source_folder=generic.source_folder,
                confidence="low",
                review_codes=("inventory_match_ambiguous",),
                review_reason=(
                    f"Content-derived scope {token_preview or 'unknown'} matched multiple existing sources: {summary}. "
                    "Kept generic routing pending confirmation."
                ).strip(),
                match_status="inventory_source_ambiguous",
                suggested_source_label="",
                suggested_source_folder="",
            )
        return _generic_unknown_resolution(scope_tokens, network_hints)

    return InventoryRouteResolution(
        source_label=default_source_label,
        source_folder=default_source_folder,
        confidence="high",
        review_codes=(),
        review_reason="",
        match_status="not_applicable",
        suggested_source_label="",
        suggested_source_folder="",
    )
