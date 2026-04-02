"""CoinTracking portfolio routing rules."""

from __future__ import annotations

import re
from pathlib import Path

from crypto_reconciliation.application.services.intake.archive import ScannedFile

COINTRACKING_CAPTURE_PATTERN = re.compile(r"as of:\s*(\d{2})\.(\d{2})\.(\d{4})", re.IGNORECASE)
CAPTURE_MONTH_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})-(?P<month>\d{2})"),
    re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})\d{4}"),
    re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?!\d)"),
)


def is_cointracking_portfolio_export(relative_path: str) -> bool:
    lower_path = relative_path.lower()
    return "cointracking" in lower_path and Path(lower_path).suffix in {".html", ".pdf"}


def is_cointracking_sidecar(relative_path: str) -> bool:
    lower_path = relative_path.lower()
    return "cointracking" in lower_path and "_files/" in lower_path


def cointracking_capture_id(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="ignore")
    match = COINTRACKING_CAPTURE_PATTERN.search(content)
    if match is None:
        return ""
    return f"{match.group(3)}-{match.group(2)}"


def cointracking_sidecar_capture_id(entry: ScannedFile, incoming_dir: Path) -> str:
    if entry.archive_member_path:
        return path_capture_id(entry.archive_source_path)
    sidecar_path = incoming_dir / entry.relative_path
    sidecar_folder = sidecar_path.parent
    if not sidecar_folder.name.endswith("_files"):
        return ""
    html_name = f"{sidecar_folder.name.removesuffix('_files')}.html"
    html_path = sidecar_folder.parent / html_name
    if not html_path.exists():
        return ""
    return cointracking_capture_id(html_path)


def path_capture_id(relative_path: str) -> str:
    for pattern in CAPTURE_MONTH_PATTERNS:
        match = pattern.search(relative_path)
        if match is None:
            continue
        return f"{match.group('year')}-{match.group('month')}"
    return ""
