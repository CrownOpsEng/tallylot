"""CoinTracking portfolio intake routing helpers."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from tallylot.ports.intake_routing import (
    IntakeFileFacts,
    IntakeRoute,
    IntakeRoutingRequest,
)

COINTRACKING_CAPTURE_PATTERN = re.compile(
    r"as of:\s*(\d{2})\.(\d{2})\.(\d{4})", re.IGNORECASE
)
PATH_DATE_PATTERNS = (
    re.compile(
        r"(?<!\d)(?P<year>20\d{2})[-_.](?P<month>\d{2})[-_.](?P<day>\d{2})(?!\d)"
    ),
    re.compile(
        r"(?<!\d)(?P<month>\d{2})[-_.](?P<day>\d{2})[-_.](?P<year>20\d{2})(?!\d)"
    ),
    re.compile(
        r"(?<!\d)(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})(?:\d{4})?(?!\d)"
    ),
)
CAPTURE_MONTH_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})-(?P<month>\d{2})"),
    re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})\d{4}"),
    re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?!\d)"),
)
PATH_YEAR_PATTERN = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
MIN_TIMESTAMP_PATTERN = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-\d{2}(?: \d{2}:\d{2}:\d{2})?$"
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
        capture_label = (
            _capture_label(request.file_path)
            or _fallback_capture_label(route_key, request.facts)
            or "unknown"
        )
        target_path = (
            request.workspace_root
            / "evidence"
            / "raw"
            / "portfolio"
            / "cointracking"
            / capture_label
            / Path(route_key).name
        )
        return IntakeRoute(
            category="portfolio_raw",
            role="portfolio_export",
            source_folder="cointracking",
            capture_label=capture_label,
            action="copy",
            target_path=target_path,
        )
    if _is_portfolio_sidecar(route_key):
        capture_label = _sidecar_capture_label(request) or "unknown"
        target_path = (
            request.workspace_root
            / "evidence"
            / "raw"
            / "portfolio"
            / "cointracking"
            / capture_label
            / _relative_target_path(route_key)
        )
        return IntakeRoute(
            category="portfolio_raw",
            role="portfolio_sidecar",
            source_folder="cointracking",
            capture_label=capture_label,
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


def _capture_label(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="ignore")
    match = COINTRACKING_CAPTURE_PATTERN.search(content)
    if match is None:
        return ""
    return f"{match.group(3)}-{match.group(2)}"


def _sidecar_capture_label(request: IntakeRoutingRequest) -> str:
    if request.archive_member_path:
        return _path_capture_label(request.archive_source_path)
    sidecar_folder = request.file_path.parent
    if not sidecar_folder.name.endswith("_files"):
        return ""
    html_name = f"{sidecar_folder.name.removesuffix('_files')}.html"
    html_path = sidecar_folder.parent / html_name
    if not html_path.exists():
        return ""
    return _capture_label(html_path)


def _path_capture_label(relative_path: str) -> str:
    parsed_dates = sorted(_parsed_path_dates(relative_path))
    if parsed_dates:
        return parsed_dates[-1].strftime("%Y-%m")
    for pattern in CAPTURE_MONTH_PATTERNS:
        match = pattern.search(relative_path)
        if match is not None:
            return f"{match.group('year')}-{match.group('month')}"
    year_match = PATH_YEAR_PATTERN.search(relative_path)
    if year_match is not None:
        return year_match.group(1)
    return ""


def _fallback_capture_label(relative_path: str, facts: IntakeFileFacts) -> str:
    match = MIN_TIMESTAMP_PATTERN.match(facts.min_timestamp.strip())
    if match is not None:
        return f"{match.group('year')}-{match.group('month')}"
    return _path_capture_label(relative_path)


def _parsed_path_dates(relative_path: str) -> list[date]:
    parsed_dates: list[date] = []
    for pattern in PATH_DATE_PATTERNS:
        for match in pattern.finditer(relative_path):
            month = int(match.group("month"))
            day = int(match.group("day"))
            year = int(match.group("year"))
            try:
                parsed_dates.append(date(year, month, day))
            except ValueError:
                continue
    return parsed_dates


def _relative_target_path(relative_path: str) -> Path:
    return Path(relative_path.replace("::", "/members/"))
