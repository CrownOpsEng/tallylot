#!/usr/bin/env python3

"""Canonical routing for historical intake files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from inspection import HistoricalDateDecision, infer_historical_date
from pipeline_common import source_slug


@dataclass(frozen=True)
class RouteTarget:
    role: str
    source_label: str
    source_folder: str
    system_label: str
    batch_slug: str
    confidence: str
    review_required: bool
    review_reason: str = ""


@dataclass(frozen=True)
class RoutingDecision:
    role: str
    source_label: str
    source_folder: str
    system_label: str
    capture_id: str
    capture_basis: str
    batch_slug: str
    destination_dir: Path
    confidence: str
    review_required: bool
    review_reason: str
    merge_recommendation: str


def _normalized_text(path: Path) -> str:
    return " / ".join(part.lower() for part in path.parts)


def classify_route(path: Path, inspection_row: dict[str, str]) -> RouteTarget:
    text = _normalized_text(path)
    name = path.name.lower()
    family = inspection_row.get("family", "")

    if "pnl calc" in text:
        return RouteTarget("working_derivative", "Binance", "binance", "", "pnl-calc", "high", False)
    if "cointracking_excel_import" in name or family == "cointracking_import_csv":
        return RouteTarget("working_derivative", "Binance", "binance", "", "cointracking-import", "high", False)
    if "cointracking" in text or "cointracking" in name:
        batch_slug = "tax-declaration" if "declaration" in text else "historical-export"
        return RouteTarget("ledger_export", "CoinTracking", "cointracking", "cointracking", batch_slug, "high", False)
    if name.startswith("bot-") or family == "trading_bot_deals_csv":
        return RouteTarget("source_raw", "3Commas", "3commas", "", "bot-export", "high", False)
    if "wealthsimple" in text:
        review_required = name.endswith(".jfif")
        return RouteTarget(
            "source_raw" if not review_required else "working_derivative",
            "WealthSimple",
            "wealthsimple",
            "",
            "historical-docs" if not review_required else "review",
            "medium" if review_required else "high",
            review_required,
            "Non-export image inside WealthSimple folder." if review_required else "",
        )
    if "coinbase" in text:
        return RouteTarget("source_raw", "Coinbase", "coinbase", "", "coinbase-pro" if "pro" in text else "retail", "high", False)
    if "coinberry" in text:
        return RouteTarget("source_raw", "Coinberry", "coinberry", "", "activity-report", "high", False)
    if "crypto.com" in text or "crypto com" in text:
        return RouteTarget("source_raw", "Crypto.com", "crypto.com", "", "historical-export", "high", False)
    if "kucoin" in text:
        return RouteTarget("source_raw", "Kucoin Main", "kucoin-main", "", "historical-export", "high", False)
    if "gemini" in text:
        return RouteTarget("source_raw", "Gemini", "gemini", "", "historical-export", "high", False)
    if "shakepay" in text:
        return RouteTarget("source_raw", "Shakepay", "shakepay", "", "historical-export", "high", False)
    if "bsc wallet export" in name or family == "explorer_transaction_csv":
        return RouteTarget("source_raw", "BSC MetaMask Wallet", "bsc-metamask1", "", "historical-explorer", "high", False)
    if "binance" in text or family.startswith("binance_margin_") or name in {"borrow.csv", "interest.csv", "liquidations.csv", "repay.csv", "trades.csv", "transfers.csv"}:
        if "archive" in text:
            batch_slug = "archive"
        elif "isolated" in text or family.startswith("binance_margin_"):
            batch_slug = "isolated-margin"
        elif "from binance" in text:
            batch_slug = "from-binance"
        else:
            batch_slug = "historical-export"
        return RouteTarget("source_raw", "Binance", "binance", "", batch_slug, "high", False)
    return RouteTarget("working_derivative", "review", "review", "", "review", "low", True, "Could not deterministically classify file role/source.")


def infer_capture_folder_name(
    *,
    repo_root: Path,
    target: RouteTarget,
    relative_path: Path,
    inspection_row: dict[str, str],
) -> tuple[str, HistoricalDateDecision, str]:
    historical = infer_historical_date(relative_path.parts, inspection_row)
    capture_id = historical.capture_id
    if capture_id == "review-required":
        capture_id = "review-required"
    if target.batch_slug and capture_id != "review-required":
        existing_base = _target_root(repo_root, target) / capture_id
        if existing_base.exists():
            capture_id = f"{capture_id}_{target.batch_slug}"
            return capture_id, historical, f"Existing capture {existing_base.name} suggests a merge candidate."
    return capture_id, historical, ""


def _target_root(repo_root: Path, target: RouteTarget) -> Path:
    if target.role == "source_raw":
        return repo_root / "01_raw_exports" / "external" / target.source_folder
    if target.role == "ledger_export":
        return repo_root / "01_raw_exports" / "cointracking" / "history"
    return repo_root / "02_working" / "supporting_artifacts" / target.source_folder


def resolve_routing_decision(
    *,
    repo_root: Path,
    incoming_root: Path,
    path: Path,
    inspection_row: dict[str, str],
) -> RoutingDecision:
    relative_path = path.resolve().relative_to(incoming_root.resolve())
    target = classify_route(relative_path, inspection_row)
    capture_folder, historical, merge_recommendation = infer_capture_folder_name(
        repo_root=repo_root,
        target=target,
        relative_path=relative_path,
        inspection_row=inspection_row,
    )
    destination_dir = _target_root(repo_root, target) / capture_folder
    review_required = target.review_required or historical.review_required
    review_reason = "; ".join(
        reason
        for reason in (target.review_reason, historical.basis if historical.review_required else "")
        if reason
    )
    return RoutingDecision(
        role=target.role,
        source_label=target.source_label,
        source_folder=target.source_folder,
        system_label=target.system_label,
        capture_id=capture_folder,
        capture_basis=historical.basis,
        batch_slug=target.batch_slug,
        destination_dir=destination_dir,
        confidence=target.confidence,
        review_required=review_required,
        review_reason=review_reason,
        merge_recommendation=merge_recommendation,
    )
