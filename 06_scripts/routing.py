#!/usr/bin/env python3

"""Canonical routing for historical intake files."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from inventory_resolution import resolve_inventory_route
from inspection import HistoricalDateDecision, HistoricalDatePolicy, infer_historical_date, inspect_file
from pipeline_common import source_slug
from raw_layout import cointracking_history_root, source_capture_root


BINANCE_ROOT_COMPANION_NAMES = {"borrow.csv", "interest.csv", "liquidations.csv", "repay.csv", "trades.csv", "transfers.csv"}


@dataclass(frozen=True)
class BundleDecision:
    bundle_id: str
    bundle_type: str
    bundle_relative_path: str


@dataclass(frozen=True)
class RouteTarget:
    role: str
    source_label: str
    source_folder: str
    system_label: str
    confidence: str
    review_codes: tuple[str, ...]
    review_reason: str = ""
    generic_wallet_routing: bool = False


@dataclass(frozen=True)
class RoutingDecision:
    role: str
    source_label: str
    source_folder: str
    system_label: str
    capture_id: str
    capture_basis: str
    date_policy: str
    destination_dir: Path
    destination_path: Path
    confidence: str
    review_required: bool
    review_reason: str
    review_codes: tuple[str, ...]
    merge_recommendation: str
    inventory_match_status: str
    inventory_match_reason: str
    suggested_source_label: str
    suggested_source_folder: str
    bundle_id: str
    bundle_type: str
    bundle_relative_path: str


def _normalized_text(path: Path) -> str:
    return " / ".join(part.lower() for part in path.parts)


def _single_file_bundle_id(path: Path) -> str:
    return source_slug(path.stem or path.name or "file")


def _folder_bundle_slug(path: Path) -> str:
    return source_slug("_".join(path.parts)) or "bundle"


def _bundle_for_path(relative_path: Path, target: RouteTarget, inspection_row: dict[str, str]) -> BundleDecision:
    name = relative_path.name
    lower_name = name.lower()
    family = inspection_row.get("family", "")
    parts = relative_path.parts

    if any(part.endswith("_files") for part in parts):
        sidecar_index = next(index for index, part in enumerate(parts) if part.endswith("_files"))
        bundle_parts = parts[: sidecar_index + 1]
        bundle_root = Path(*bundle_parts)
        bundle_parent = bundle_root.parent
        bundle_label = bundle_root.name.removesuffix("_files")
        bundle_id = source_slug(bundle_label) or "html-export"
        bundle_relative_path = str(relative_path.relative_to(bundle_parent))
        return BundleDecision(bundle_id=bundle_id, bundle_type="html_export_bundle", bundle_relative_path=bundle_relative_path)

    if lower_name.endswith(".html") and "cointracking" in lower_name:
        return BundleDecision(
            bundle_id=source_slug(relative_path.stem) or "html-export",
            bundle_type="html_export_bundle",
            bundle_relative_path=name,
        )

    if lower_name in BINANCE_ROOT_COMPANION_NAMES and len(parts) == 1 and target.source_folder == "binance":
        return BundleDecision(
            bundle_id="binance-isolated-margin-loose",
            bundle_type="synthetic_companion_bundle",
            bundle_relative_path=name,
        )

    if family.endswith("_archive_bundle") or lower_name.endswith((".zip", ".tar", ".tgz", ".tar.gz")):
        return BundleDecision(bundle_id=_single_file_bundle_id(relative_path), bundle_type="archive_bundle", bundle_relative_path=str(Path("archive") / name))

    if len(parts) > 1:
        bundle_root = relative_path.parent
        return BundleDecision(
            bundle_id=_folder_bundle_slug(bundle_root),
            bundle_type="folder_bundle",
            bundle_relative_path=name,
        )

    return BundleDecision(bundle_id=_single_file_bundle_id(relative_path), bundle_type="single_file_bundle", bundle_relative_path=name)


def _base_route_target(path: Path, inspection_row: dict[str, str]) -> RouteTarget:
    text = _normalized_text(path)
    name = path.name.lower()
    family = inspection_row.get("family", "")
    archive_source = inspection_row.get("archive_detected_source", "")
    archive_status = inspection_row.get("archive_inspection_status", "")
    archive_findings = inspection_row.get("archive_findings", "")

    if "pnl calc" in text:
        return RouteTarget("working_derivative", "Binance", "binance", "", "high", ())
    if "cointracking_excel_import" in name or family == "cointracking_import_csv":
        return RouteTarget("working_derivative", "Binance", "binance", "", "high", ())
    if archive_source == "CoinTracking":
        return RouteTarget("portfolio_export", "CoinTracking", "cointracking", "cointracking", "high", ())
    if archive_source == "Binance":
        return RouteTarget("source_raw", "Binance", "binance", "", "high", ())
    if archive_source == "WealthSimple":
        return RouteTarget("source_raw", "WealthSimple", "wealthsimple", "", "high", ())
    if archive_source == "Kucoin Main":
        return RouteTarget("source_raw", "Kucoin Main", "kucoin-main", "", "high", ())
    if "cointracking" in text or "cointracking" in name or family.startswith("cointracking_"):
        return RouteTarget("portfolio_export", "CoinTracking", "cointracking", "cointracking", "high", ())
    if name.startswith("bot-") or family == "trading_bot_deals_csv":
        return RouteTarget("source_raw", "3Commas", "3commas", "", "high", ())
    if "wealthsimple" in text:
        if name.endswith(".jfif"):
            return RouteTarget("working_derivative", "WealthSimple", "wealthsimple", "", "medium", ("non_export_artifact",), "Non-export image inside WealthSimple folder.")
        return RouteTarget("source_raw", "WealthSimple", "wealthsimple", "", "high", ())
    if "coinbase" in text:
        return RouteTarget("source_raw", "Coinbase", "coinbase", "", "high", ())
    if "coinberry" in text:
        return RouteTarget("source_raw", "Coinberry", "coinberry", "", "high", ())
    if "crypto.com" in text or "crypto com" in text:
        return RouteTarget("source_raw", "Crypto.com", "crypto.com", "", "high", ())
    if "kucoin" in text or "kucoin" in inspection_row.get("header_preview", "").lower():
        return RouteTarget("source_raw", "Kucoin Main", "kucoin-main", "", "high", ())
    if "gemini" in text:
        return RouteTarget("source_raw", "Gemini", "gemini", "", "high", ())
    if "shakepay" in text:
        return RouteTarget("source_raw", "Shakepay", "shakepay", "", "high", ())
    if family in {"coinberry_activity_csv", "shakepay_transactions_csv", "gemini_account_history_csv", "binance_staking_redemption_csv"}:
        if family == "coinberry_activity_csv":
            return RouteTarget("source_raw", "Coinberry", "coinberry", "", "high", ())
        if family == "shakepay_transactions_csv":
            return RouteTarget("source_raw", "Shakepay", "shakepay", "", "high", ())
        if family == "gemini_account_history_csv":
            return RouteTarget("source_raw", "Gemini", "gemini", "", "high", ())
        return RouteTarget("source_raw", "Binance", "binance", "", "high", ())
    if "bsc wallet export" in name or family.startswith("explorer_"):
        return RouteTarget("source_raw", "Wallet Export", "wallet-export", "", "medium", (), generic_wallet_routing=True)
    if family.startswith("near_"):
        return RouteTarget("source_raw", "Wallet Export", "wallet-export", "", "medium", (), generic_wallet_routing=True)
    if family == "derivatives_report_csv" or "gtrade" in text:
        return RouteTarget("source_raw", "GTrade 1CT", "gtrade", "", "high", ())
    if "binance" in text or family.startswith("binance_margin_") or family == "binance_archive_bundle" or name in BINANCE_ROOT_COMPANION_NAMES:
        return RouteTarget("source_raw", "Binance", "binance", "", "high", ())
    if "isolated" in text and family.endswith("_bundle"):
        return RouteTarget("source_raw", "Binance", "binance", "", "medium", ("unsupported_inspection",), "Archive requires review to confirm Binance export family.")
    if archive_status == "review":
        return RouteTarget("working_derivative", "review", "review", "", "low", ("archive_contents_review",), archive_findings or "Archive contents need review.")
    return RouteTarget("working_derivative", "review", "review", "", "low", ("unsupported_routing",), "Could not deterministically classify file role/source.")


def classify_route(path: Path, inspection_row: dict[str, str]) -> RouteTarget:
    base_target = _base_route_target(path, inspection_row)
    artifact_kind = inspection_row.get("artifact_kind", "")
    artifact_reason = inspection_row.get("artifact_reason", "") or "Non-export artifact."
    if not artifact_kind:
        return base_target

    source_label = base_target.source_label if base_target.source_folder != "review" else "review"
    source_folder = base_target.source_folder if base_target.source_folder != "review" else "review"
    confidence = "high" if source_folder != "review" else "medium"
    review_codes: tuple[str, ...] = ()

    if artifact_kind in {"image_artifact", "xps_document"}:
        review_codes = ("non_export_artifact",)

    return RouteTarget(
        role="working_derivative",
        source_label=source_label,
        source_folder=source_folder,
        system_label="",
        confidence=confidence,
        review_codes=review_codes,
        review_reason=artifact_reason if review_codes else "",
        generic_wallet_routing=base_target.generic_wallet_routing,
    )


def date_policy_for_target(target: RouteTarget, bundle: BundleDecision, inspection_row: dict[str, str]) -> tuple[str, HistoricalDatePolicy]:
    family = inspection_row.get("family", "")
    if target.role == "portfolio_export" or family.startswith("cointracking_"):
        return "portfolio_export_capture", HistoricalDatePolicy(allow_content_span=False)
    if bundle.bundle_type in {"archive_bundle", "html_export_bundle"}:
        return "bundle_export_timestamp", HistoricalDatePolicy(allow_content_span=False)
    if family.startswith("binance_margin_") or family in {"trading_bot_deals_csv", "fills_csv", "transfer_statement_csv", "custodial_transaction_csv"}:
        return "ranged_or_content_source_export", HistoricalDatePolicy()
    return "generic_historical_capture", HistoricalDatePolicy()


@lru_cache(maxsize=64)
def _cached_inspect_file(path: str) -> dict[str, str]:
    return inspect_file(Path(path))


def _bundle_historical_context(
    *,
    incoming_root: Path,
    relative_path: Path,
    bundle: BundleDecision,
    inspection_row: dict[str, str],
) -> dict[str, str]:
    if bundle.bundle_type != "html_export_bundle" or inspection_row.get("export_timestamp"):
        return inspection_row
    try:
        sidecar_index = next(index for index, part in enumerate(relative_path.parts) if part.endswith("_files"))
    except StopIteration:
        return inspection_row
    sidecar_dir = Path(*relative_path.parts[: sidecar_index + 1])
    bundle_label = sidecar_dir.name.removesuffix("_files")
    html_path = incoming_root / sidecar_dir.parent / f"{bundle_label}.html"
    if not html_path.exists():
        return inspection_row
    parent_row = _cached_inspect_file(str(html_path.resolve()))
    inherited = dict(inspection_row)
    for field in ("export_timestamp", "report_period_start", "report_period_end"):
        if not inherited.get(field):
            inherited[field] = parent_row.get(field, "")
    return inherited


def infer_capture_folder_name(
    *,
    repo_root: Path,
    incoming_root: Path,
    target: RouteTarget,
    relative_path: Path,
    inspection_row: dict[str, str],
    bundle: BundleDecision,
) -> tuple[str, str, HistoricalDateDecision, str]:
    date_policy, historical_policy = date_policy_for_target(target, bundle, inspection_row)
    historical_row = _bundle_historical_context(
        incoming_root=incoming_root,
        relative_path=relative_path,
        bundle=bundle,
        inspection_row=inspection_row,
    )
    historical = infer_historical_date(relative_path.parts, historical_row, policy=historical_policy)
    capture_id = historical.capture_id
    merge_recommendation = ""
    if capture_id != "review-required":
        existing_capture = _target_root(repo_root, target) / capture_id
        if existing_capture.exists():
            merge_recommendation = f"Existing capture {capture_id} already exists; compare bundle overlap before merging."
    return capture_id, date_policy, historical, merge_recommendation


def _target_root(repo_root: Path, target: RouteTarget) -> Path:
    if target.role == "source_raw":
        return source_capture_root(repo_root, target.source_folder)
    if target.role == "portfolio_export":
        return cointracking_history_root(repo_root)
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
    inventory_resolution = resolve_inventory_route(
        repo_root=repo_root,
        relative_path=relative_path,
        inspection_row=inspection_row,
        default_source_label=target.source_label,
        default_source_folder=target.source_folder,
        generic_wallet_routing=target.generic_wallet_routing,
    )
    target = RouteTarget(
        role=target.role,
        source_label=inventory_resolution.source_label,
        source_folder=inventory_resolution.source_folder,
        system_label=target.system_label,
        confidence=inventory_resolution.confidence if target.generic_wallet_routing else target.confidence,
        review_codes=tuple(dict.fromkeys((*target.review_codes, *inventory_resolution.review_codes))),
        review_reason="; ".join(part for part in [target.review_reason, inventory_resolution.review_reason] if part),
        generic_wallet_routing=target.generic_wallet_routing,
    )
    bundle = _bundle_for_path(relative_path, target, inspection_row)
    capture_folder, date_policy, historical, merge_recommendation = infer_capture_folder_name(
        repo_root=repo_root,
        incoming_root=incoming_root,
        target=target,
        relative_path=relative_path,
        inspection_row=inspection_row,
        bundle=bundle,
    )
    capture_dir = _target_root(repo_root, target) / capture_folder
    destination_dir = capture_dir / bundle.bundle_id
    destination_path = destination_dir / bundle.bundle_relative_path

    review_codes = list(target.review_codes)
    if historical.review_required:
        review_codes.append("unresolved_historical_date")
    review_required = bool(review_codes)
    review_reason_parts = [target.review_reason]
    if historical.review_required:
        review_reason_parts.append(historical.basis)
    review_reason = "; ".join(part for part in review_reason_parts if part)

    return RoutingDecision(
        role=target.role,
        source_label=target.source_label,
        source_folder=target.source_folder,
        system_label=target.system_label,
        capture_id=capture_folder,
        capture_basis=historical.basis,
        date_policy=date_policy,
        destination_dir=destination_dir,
        destination_path=destination_path,
        confidence=target.confidence,
        review_required=review_required,
        review_reason=review_reason,
        review_codes=tuple(dict.fromkeys(review_codes)),
        merge_recommendation=merge_recommendation,
        inventory_match_status=inventory_resolution.match_status,
        inventory_match_reason=inventory_resolution.review_reason,
        suggested_source_label=inventory_resolution.suggested_source_label,
        suggested_source_folder=inventory_resolution.suggested_source_folder,
        bundle_id=bundle.bundle_id,
        bundle_type=bundle.bundle_type,
        bundle_relative_path=bundle.bundle_relative_path,
    )
