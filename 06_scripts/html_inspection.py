#!/usr/bin/env python3

"""Dedicated HTML inspection helpers for saved ledger exports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


TITLE_PATTERN = re.compile(r"<title>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)
COINTRACKING_CREATED_PATTERN = re.compile(r"Created by:.*?as of:\s*(?P<value>\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})", re.IGNORECASE | re.DOTALL)
COINTRACKING_PERIOD_PATTERN = re.compile(
    r"period from\s*<strong>(?P<start>\d{2}\.\d{2}\.\d{4})</strong>\s*until\s*<strong>(?P<end>\d{2}\.\d{2}\.\d{4})</strong>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class HtmlInspection:
    family: str
    header_preview: str
    export_timestamp: str
    report_period_start: str
    report_period_end: str

    def to_row(self) -> dict[str, str]:
        return {
            "family": self.family,
            "header_preview": self.header_preview,
            "export_timestamp": self.export_timestamp,
            "report_period_start": self.report_period_start,
            "report_period_end": self.report_period_end,
        }


def _parse_dot_date(value: str, *, with_time: bool = False) -> str:
    text = value.strip()
    if not text:
        return ""
    fmt = "%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y"
    try:
        return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S" if with_time else "%Y-%m-%d 00:00:00")
    except ValueError:
        return ""


def inspect_html(path: Path) -> HtmlInspection | None:
    if path.suffix.lower() != ".html":
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    title_match = TITLE_PATTERN.search(text)
    title = " ".join((title_match.group("title") if title_match else "").split())
    if "cointracking" not in title.lower() and "cointracking" not in text.lower():
        return None

    family = "cointracking_saved_html"
    if "tax declaration export" in title.lower():
        family = "cointracking_tax_declaration_html"
    created_match = COINTRACKING_CREATED_PATTERN.search(text)
    period_match = COINTRACKING_PERIOD_PATTERN.search(text)
    return HtmlInspection(
        family=family,
        header_preview=title,
        export_timestamp=_parse_dot_date(created_match.group("value"), with_time=True) if created_match else "",
        report_period_start=_parse_dot_date(period_match.group("start")) if period_match else "",
        report_period_end=_parse_dot_date(period_match.group("end")) if period_match else "",
    )
