#!/usr/bin/env python3

"""Adapter registry for universal source profiling and normalization."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence

from coinbase_common import (
    coinbase_balance_rows_from_text,
    csv_dict_rows,
    normalize_coinbase_transactions,
    retail_csv_rows,
)
from pipeline_common import CANONICAL_BALANCE_HEADERS, CANONICAL_EVENT_HEADERS, EXCEPTION_HEADERS, SourceProfile
from script_common import extract_pdf_text, read_cointracking_rows


DECISION_HEADERS = (
    "manifest_fingerprint",
    "event_id",
    "resolution_status",
    "resolution_note",
)


@dataclass(frozen=True)
class AdapterNormalizationResult:
    canonical_events: list[dict[str, str]]
    canonical_balances: list[dict[str, str]]
    exceptions: list[dict[str, str]]


def default_exception_row(
    *,
    manifest_fingerprint: str,
    source: str,
    adapter: str,
    event_id: str,
    raw_file: str,
    raw_row_ref: str,
    exception_kind: str,
    message: str,
    resolution_status: str = "",
    resolution_note: str = "",
) -> dict[str, str]:
    return {
        "manifest_fingerprint": manifest_fingerprint,
        "event_id": event_id,
        "source": source,
        "adapter": adapter,
        "raw_file": raw_file,
        "raw_row_ref": raw_row_ref,
        "exception_kind": exception_kind,
        "message": message,
        "status": "needs_review",
        "resolution_status": resolution_status,
        "resolution_note": resolution_note,
    }


def ct_row_to_canonical_event(row: dict[str, str], adapter_name: str, source_name: str) -> dict[str, str]:
    return {
        "event_id": row["Tx-ID"] or f"{adapter_name}:{row['raw_file']}:{row['raw_row_ref']}",
        "source": source_name,
        "adapter": adapter_name,
        "account": row["Exchange"],
        "wallet": row["Exchange"],
        "raw_file": row["raw_source"],
        "raw_row_ref": row["raw_ref"],
        "timestamp": row["Date"],
        "event_kind": row["Type"],
        "asset_in": row["Buy Cur."],
        "amount_in": row["Buy"],
        "asset_out": row["Sell Cur."],
        "amount_out": row["Sell"],
        "fee_asset": row["Fee Cur."],
        "fee_amount": row["Fee"],
        "tx_hash": row["Tx-ID"],
        "description": row["Comment"],
        "confidence": "high",
        "status": "mapped",
        "render_type": row["Type"],
        "render_exchange": row["Exchange"],
        "render_group": row["Group"],
        "render_comment": row["Comment"],
        "render_comment_mode": row["comment_mode"],
        "render_tx_id": row["Tx-ID"],
        "render_tx_id_mode": row["tx_id_mode"],
        "render_allowed_types": row["allowed_types"],
        "render_match_window_seconds": row["match_window_seconds"],
        "render_fee_tolerance": row["fee_tolerance"],
        "render_notes": row["notes"],
    }


def load_exception_decisions(path: Path | None, manifest_fingerprint: str) -> dict[str, dict[str, str]]:
    if path is None or not path.exists():
        return {}
    rows = read_cointracking_rows(path) if path.suffix.lower() == ".csv" and path.name.endswith("_ct.csv") else []
    if rows:
        return {}
    import csv

    decisions: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("manifest_fingerprint") != manifest_fingerprint:
                continue
            event_id = row.get("event_id", "")
            if not event_id:
                continue
            decisions[event_id] = {
                "resolution_status": row.get("resolution_status", ""),
                "resolution_note": row.get("resolution_note", ""),
            }
    return decisions


class SourceAdapter:
    name = "base"
    aliases: tuple[str, ...] = ()
    supported = False

    def matches(self, source: str) -> bool:
        slug = source.strip().lower()
        return slug == self.name or slug in self.aliases

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        exception = default_exception_row(
            manifest_fingerprint=profile.manifest_fingerprint,
            source=profile.source,
            adapter=self.name,
            event_id=f"{self.name}:adapter_not_implemented",
            raw_file="",
            raw_row_ref="",
            exception_kind="adapter_not_implemented",
            message=f"No deterministic normalization adapter has been implemented for {profile.source}.",
            resolution_status=exception_decisions.get(f"{self.name}:adapter_not_implemented", {}).get("resolution_status", ""),
            resolution_note=exception_decisions.get(f"{self.name}:adapter_not_implemented", {}).get("resolution_note", ""),
        )
        exceptions = [] if exception["resolution_status"] == "accepted" else [exception]
        return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)


class CoinbaseAdapter(SourceAdapter):
    name = "coinbase"
    aliases = ("coinbase",)
    supported = True

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        retail_path = None
        pro_statement_paths: list[Path] = []
        pro_fill_paths: list[Path] = []
        pdf_paths: list[Path] = []

        for path in sorted(raw_dir.iterdir()):
            if not path.is_file():
                continue
            name = path.name
            if "Statement - All Time" in name and path.suffix.lower() == ".csv":
                retail_path = path
            elif "Coinbase Pro - Statement" in name and path.suffix.lower() == ".csv":
                pro_statement_paths.append(path)
            elif "Coinbase Pro - Fills" in name and path.suffix.lower() == ".csv":
                pro_fill_paths.append(path)
            elif path.suffix.lower() == ".pdf":
                pdf_paths.append(path)

        exceptions: list[dict[str, str]] = []
        if retail_path is None:
            missing = default_exception_row(
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="coinbase:missing_retail_csv",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="Coinbase retail all-time CSV is required for deterministic normalization.",
                resolution_status=exception_decisions.get("coinbase:missing_retail_csv", {}).get("resolution_status", ""),
                resolution_note=exception_decisions.get("coinbase:missing_retail_csv", {}).get("resolution_note", ""),
            )
            if missing["resolution_status"] != "accepted":
                exceptions.append(missing)
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        normalized_rows = normalize_coinbase_transactions(
            retail_csv_rows(retail_path),
            [dict(row, _file=path.name) for path in pro_statement_paths for row in csv_dict_rows(path, "Coinbase Pro statement CSV")],
            [dict(row, _file=path.name) for path in pro_fill_paths for row in csv_dict_rows(path, "Coinbase Pro fills CSV")],
            retail_source=retail_path,
        )

        events = [ct_row_to_canonical_event(row, self.name, profile.source) for row in normalized_rows]
        balances: list[dict[str, str]] = []
        for pdf_path in pdf_paths:
            balances.extend(coinbase_balance_rows_from_text(extract_pdf_text(pdf_path), pdf_path.name))
        return AdapterNormalizationResult(canonical_events=events, canonical_balances=balances, exceptions=exceptions)


class WealthsimpleAdapter(SourceAdapter):
    name = "wealthsimple"
    aliases = ("wealthsimple", "wealthsimple crypto")


class BinanceAdapter(SourceAdapter):
    name = "binance"
    aliases = ("binance",)


class MetamaskAdapter(SourceAdapter):
    name = "metamask"
    aliases = ("metamask", "bsc metamask wallet", "eth metamask wallet", "metamask - polygon")


class ShakepayAdapter(SourceAdapter):
    name = "shakepay"
    aliases = ("shakepay",)


class LedgerLiveAdapter(SourceAdapter):
    name = "ledger_live"
    aliases = ("ledger live", "ada ledger")


class NearAdapter(SourceAdapter):
    name = "near"
    aliases = ("near", "near wallet", "near wallet - staking")


ADAPTERS: tuple[SourceAdapter, ...] = (
    CoinbaseAdapter(),
    WealthsimpleAdapter(),
    BinanceAdapter(),
    MetamaskAdapter(),
    ShakepayAdapter(),
    LedgerLiveAdapter(),
    NearAdapter(),
)


def get_adapter(source: str) -> SourceAdapter:
    for adapter in ADAPTERS:
        if adapter.matches(source):
            return adapter
    fallback = SourceAdapter()
    fallback.name = "generic"
    fallback.aliases = ()
    return fallback


def available_adapter_rows() -> list[dict[str, str]]:
    return [
        {
            "adapter": adapter.name,
            "supported": "yes" if adapter.supported else "no",
            "aliases": ", ".join(adapter.aliases),
        }
        for adapter in ADAPTERS
    ]

