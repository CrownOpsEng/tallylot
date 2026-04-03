"""CoinTracking portfolio intake routing helpers."""

from __future__ import annotations

import re
from pathlib import Path

from crypto_reconciliation.application.services.intake.file_facts import detect_capture_id
from crypto_reconciliation.application.services.intake.routing.targets import relative_target_path
from crypto_reconciliation.ports.intake_routing import IntakeRoute, IntakeRoutingRequest

COINTRACKING_CAPTURE_PATTERN = re.compile(r"as of:\s*(\d{2})\.(\d{2})\.(\d{4})", re.IGNORECASE)
CAPTURE_MONTH_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})-(?P<month>\d{2})"),
    re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})\d{4}"),
    re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?!\d)"),
)


def match_intake(relative_path: str) -> int:
    lower_path = relative_path.lower()
    if "cointracking" not in lower_path:
        return 0
    if "_files/" in lower_path:
        return 100
    if Path(lower_path).suffix in {".html", ".pdf"}:
        return 100
    return 0


def route_intake(request: IntakeRoutingRequest) -> IntakeRoute | None:
    route_key = request.route_key
    if _is_portfolio_export(route_key):
        capture_id = _capture_id(request.file_path) or detect_capture_id(route_key, request.facts) or "unknown"
        target_path = (
            request.workspace_root
            / "evidence"
            / "raw"
            / "portfolio"
            / "cointracking"
            / capture_id
            / Path(route_key).name
        )
        return IntakeRoute(
            category="portfolio_raw",
            role="portfolio_export",
            source_folder="cointracking",
            capture_id=capture_id,
            action="copy",
            target_path=target_path,
        )
    if _is_portfolio_sidecar(route_key):
        capture_id = _sidecar_capture_id(request) or "unknown"
        target_path = (
            request.workspace_root
            / "evidence"
            / "raw"
            / "portfolio"
            / "cointracking"
            / capture_id
            / relative_target_path(route_key)
        )
        return IntakeRoute(
            category="portfolio_raw",
            role="portfolio_sidecar",
            source_folder="cointracking",
            capture_id=capture_id,
            action="extract_copy" if request.archive_member_path else "copy",
            target_path=target_path,
        )
    return None


def _is_portfolio_export(relative_path: str) -> bool:
    lower_path = relative_path.lower()
    return "cointracking" in lower_path and Path(lower_path).suffix in {".html", ".pdf"}


def _is_portfolio_sidecar(relative_path: str) -> bool:
    lower_path = relative_path.lower()
    return "cointracking" in lower_path and "_files/" in lower_path


def _capture_id(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="ignore")
    match = COINTRACKING_CAPTURE_PATTERN.search(content)
    if match is None:
        return ""
    return f"{match.group(3)}-{match.group(2)}"


def _sidecar_capture_id(request: IntakeRoutingRequest) -> str:
    if request.archive_member_path:
        return _path_capture_id(request.archive_source_path)
    sidecar_folder = request.file_path.parent
    if not sidecar_folder.name.endswith("_files"):
        return ""
    html_name = f"{sidecar_folder.name.removesuffix('_files')}.html"
    html_path = sidecar_folder.parent / html_name
    if not html_path.exists():
        return ""
    return _capture_id(html_path)


def _path_capture_id(relative_path: str) -> str:
    for pattern in CAPTURE_MONTH_PATTERNS:
        match = pattern.search(relative_path)
        if match is not None:
            return f"{match.group('year')}-{match.group('month')}"
    return ""
