"""Binance intake routing helpers."""

from __future__ import annotations

import re
from pathlib import Path

from tallylot.adapters.support import match_intake_by_path_or_header
from tallylot.ports.intake_routing import (
    IntakeFileFacts,
    IntakeRoute,
    IntakeRoutingRequest,
)

from .statement_evidence import STATEMENT_PERIOD_PATTERN

_RAW_WORKBOOK_PATTERNS = (
    re.compile(
        r"^binance(?:-| )order history(?: report)? \d{4}\.(?:xlsx|xls)$", re.IGNORECASE
    ),
    re.compile(
        r"^binance(?:-| )withdrawal history report \d{4}\.(?:xlsx|xls)$", re.IGNORECASE
    ),
)


def match_intake(relative_path: str, facts: IntakeFileFacts) -> int:
    return match_intake_by_path_or_header(
        relative_path,
        facts,
        path_hints=("binance", "accountstatementperiod"),
        header_hints=(
            "pair,coin,date,amount,type,status",
            "pair,coin,amount,time,interest type",
            "date(utc),pair,side,price,executed,amount,fee",
        ),
    )


def route_intake(request: IntakeRoutingRequest) -> IntakeRoute | None:
    if not _is_raw_binance_source_evidence(request.relative_path):
        return None
    return IntakeRoute(
        category="source_raw",
        role="source_export",
        source_folder="binance",
        capture_label=request.incoming_dir.name,
        action="extract_copy" if request.archive_member_path else "copy",
        target_path=_raw_binance_source_target_path(request),
    )


def _is_raw_binance_source_evidence(relative_path: str) -> bool:
    filename = Path(relative_path).name
    return any(pattern.match(filename) for pattern in _RAW_WORKBOOK_PATTERNS) or (
        filename.lower().endswith(".pdf")
        and STATEMENT_PERIOD_PATTERN.search(filename) is not None
    )


def _raw_binance_source_target_path(request: IntakeRoutingRequest) -> Path:
    capture_root = (
        request.workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "binance"
        / request.incoming_dir.name
    )
    if request.archive_member_path:
        archive_stem = Path(request.archive_source_path).stem
        return (
            capture_root / archive_stem / "contents" / Path(request.archive_member_path)
        )
    return capture_root / Path(request.relative_path)
