"""Typed intake routing rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.application.services.archive_scan import ScannedFile

COINTRACKING_CAPTURE_PATTERN = re.compile(r"as of:\s*(\d{2})\.(\d{2})\.(\d{4})", re.IGNORECASE)
CAPTURE_MONTH_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})-(?P<month>\d{2})"),
    re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})\d{4}"),
)
SOURCE_FOLDER_HINTS = (
    ("wealthsimple", "wealthsimple"),
    ("coinbase", "coinbase"),
    ("binance", "binance"),
    ("crypto.com", "crypto_com"),
    ("crypto_com", "crypto_com"),
    ("shakepay", "shakepay"),
    ("ledger", "ledger_live"),
    ("near", "near"),
    ("gtrade", "gtrade"),
    ("metamask", "evm_wallet"),
    ("state logs", "evm_wallet"),
    ("etherscan", "evm_explorer"),
    ("arbiscan", "evm_explorer"),
    ("polygonscan", "evm_explorer"),
    ("bsc", "evm_explorer"),
    ("evm", "evm_explorer"),
)
RAW_SOURCE_SUFFIXES = frozenset({".csv", ".json", ".zip"})
WORKING_DERIVATIVE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".xlsx", ".xls"})
HEADER_SOURCE_HINTS = (
    ("pair,coin,date,amount,type,status", "binance"),
    ("pair,coin,amount,time,interest type", "binance"),
    ("date(utc),pair,side,price,executed,amount,fee", "binance"),
    ("portfolio,type,time,amount,balance,amount/balance unit", "coinbase"),
)


@dataclass(frozen=True)
class IntakeRoute:
    category: str
    role: str
    source_folder: str
    capture_id: str
    action: str
    target_path: Path
    inventory_match_status: str = "unmatched"
    review_required: str = "no"
    review_codes: str = ""
    review_reason: str = ""


def route_intake_file(
    entry: ScannedFile,
    *,
    incoming_dir: Path,
    workspace_root: Path,
) -> IntakeRoute:
    route_key = (
        f"{entry.archive_source_path}::{entry.archive_member_path}"
        if entry.archive_member_path
        else entry.relative_path
    )
    if _is_cointracking_html(route_key):
        capture_id = _cointracking_capture_id(entry.file_path) or "unknown"
        target_path = (
            workspace_root / "evidence" / "raw" / "portfolio" / "cointracking" / capture_id / Path(route_key).name
        )
        return IntakeRoute(
            category="portfolio_raw",
            role="portfolio_export",
            source_folder="cointracking",
            capture_id=capture_id,
            action="copy",
            target_path=target_path,
        )

    if _is_cointracking_sidecar(route_key):
        capture_id = _cointracking_sidecar_capture_id(entry, incoming_dir) or "unknown"
        relative_target = _relative_target_path(route_key)
        target_path = workspace_root / "evidence" / "raw" / "portfolio" / "cointracking" / capture_id / relative_target
        return IntakeRoute(
            category="portfolio_raw",
            role="portfolio_sidecar",
            source_folder="cointracking",
            capture_id=capture_id,
            action="extract_copy" if entry.archive_member_path else "copy",
            target_path=target_path,
        )

    source_folder = detect_source_folder(route_key, entry.file_path)
    capture_id = detect_capture_id(route_key) or incoming_dir.name
    relative_target = _relative_target_path(route_key)
    if _is_working_derivative(route_key):
        return IntakeRoute(
            category="supporting_artifact",
            role="working_derivative",
            source_folder=source_folder,
            capture_id=capture_id,
            action="extract_copy" if entry.archive_member_path else "copy",
            target_path=(
                workspace_root
                / "working"
                / "supporting_artifacts"
                / source_folder
                / incoming_dir.name
                / relative_target
            ),
        )
    if Path(route_key).suffix.lower() in RAW_SOURCE_SUFFIXES:
        target_path = _raw_source_target_path(
            entry,
            workspace_root=workspace_root,
            source_folder=source_folder,
            capture_id=capture_id,
            relative_target=relative_target,
        )
        return IntakeRoute(
            category="source_raw",
            role="source_export",
            source_folder=source_folder,
            capture_id=capture_id,
            action="extract_copy" if entry.archive_member_path else "copy",
            target_path=target_path,
        )
    return IntakeRoute(
        category="supporting_artifact",
        role="supporting_artifact",
        source_folder=source_folder,
        capture_id=capture_id,
        action="extract_copy" if entry.archive_member_path else "copy",
        target_path=(
            workspace_root / "working" / "supporting_artifacts" / source_folder / incoming_dir.name / relative_target
        ),
    )


def detect_source_folder(relative_path: str, file_path: Path) -> str:
    lower_path = relative_path.lower()
    for hint, source_folder in SOURCE_FOLDER_HINTS:
        if hint in lower_path:
            return source_folder
    if file_path.suffix.lower() == ".csv":
        header_lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if header_lines:
            normalized_header = header_lines[0].strip().lower()
            for header_hint, source_folder in HEADER_SOURCE_HINTS:
                if header_hint in normalized_header:
                    return source_folder
    return "unclassified"


def detect_capture_id(relative_path: str) -> str:
    for pattern in CAPTURE_MONTH_PATTERNS:
        match = pattern.search(relative_path)
        if match is None:
            continue
        return f"{match.group('year')}-{match.group('month')}"
    return ""


def _is_cointracking_html(relative_path: str) -> bool:
    lower_path = relative_path.lower()
    return lower_path.endswith(".html") and "cointracking" in lower_path


def _is_cointracking_sidecar(relative_path: str) -> bool:
    lower_path = relative_path.lower()
    return "cointracking" in lower_path and "_files/" in lower_path


def _cointracking_capture_id(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="ignore")
    match = COINTRACKING_CAPTURE_PATTERN.search(content)
    if match is None:
        return ""
    return f"{match.group(3)}-{match.group(2)}"


def _cointracking_sidecar_capture_id(entry: ScannedFile, incoming_dir: Path) -> str:
    if entry.archive_member_path:
        return detect_capture_id(entry.archive_source_path)
    sidecar_path = incoming_dir / entry.relative_path
    sidecar_folder = sidecar_path.parent
    if not sidecar_folder.name.endswith("_files"):
        return ""
    html_name = f"{sidecar_folder.name.removesuffix('_files')}.html"
    html_path = sidecar_folder.parent / html_name
    if not html_path.exists():
        return ""
    return _cointracking_capture_id(html_path)


def _is_working_derivative(relative_path: str) -> bool:
    path = Path(relative_path.replace("::", "__"))
    return path.suffix.lower() in WORKING_DERIVATIVE_SUFFIXES or path.name.lower() == "test.csv"


def _relative_target_path(relative_path: str) -> Path:
    return Path(relative_path.replace("::", "/members/"))


def _raw_source_target_path(
    entry: ScannedFile,
    *,
    workspace_root: Path,
    source_folder: str,
    capture_id: str,
    relative_target: Path,
) -> Path:
    base_path = workspace_root / "evidence" / "raw" / "source" / source_folder / capture_id
    if entry.archive_member_path:
        archive_stem = Path(entry.archive_source_path).stem
        return base_path / archive_stem / "contents" / Path(entry.archive_member_path)
    if Path(entry.relative_path).suffix.lower() == ".zip":
        archive_stem = Path(entry.relative_path).stem
        return base_path / archive_stem / "archive" / Path(entry.relative_path).name
    return base_path / relative_target
