#!/usr/bin/env python3

"""Dedicated XLSX workbook inspection helpers."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from file_family import classify_file_family
from scope_identity import csv_scope_tokens
from tabular_inspection import TabularAnalysis, analyze_tabular_rows, detect_header_from_rows


XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "office": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "package": "http://schemas.openxmlformats.org/package/2006/relationships",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dcterms": "http://purl.org/dc/terms/",
}

EXCEL_EPOCH = datetime(1899, 12, 30)
COINTRACKING_HEADERS = {"date", "type", "buy amount", "buy cur.", "sell amount", "sell cur.", "fee amount", "fee amount (optional)"}


@dataclass(frozen=True)
class WorkbookInspection:
    family: str
    header_preview: str
    data_rows: str
    date_field: str
    min_timestamp: str
    max_timestamp: str
    timestamp_resolution: str
    timezone_mode: str
    timezone_value: str
    timezone_conflict: str
    scope_tokens: tuple[str, ...]
    export_timestamp: str
    workbook_sheet_names: str
    workbook_created_at: str
    workbook_modified_at: str

    def to_row(self) -> dict[str, str]:
        return {
            "family": self.family,
            "header_preview": self.header_preview,
            "data_rows": self.data_rows,
            "date_field": self.date_field,
            "min_timestamp": self.min_timestamp,
            "max_timestamp": self.max_timestamp,
            "timestamp_resolution": self.timestamp_resolution,
            "timezone_mode": self.timezone_mode,
            "timezone_value": self.timezone_value,
            "timezone_conflict": self.timezone_conflict,
            "content_scope_tokens": ";".join(self.scope_tokens),
            "export_timestamp": self.export_timestamp,
            "workbook_sheet_names": self.workbook_sheet_names,
            "workbook_created_at": self.workbook_created_at,
            "workbook_modified_at": self.workbook_modified_at,
        }


def _join_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _parse_iso_timestamp(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return ""


def _load_shared_strings(handle: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in handle.namelist():
        return []
    root = ET.fromstring(handle.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("main:si", XML_NS):
        values.append(_join_text(item))
    return values


def _load_sheet_names(handle: zipfile.ZipFile) -> list[str]:
    if "xl/workbook.xml" not in handle.namelist():
        return []
    root = ET.fromstring(handle.read("xl/workbook.xml"))
    return [sheet.get("name", "").strip() for sheet in root.findall("main:sheets/main:sheet", XML_NS) if sheet.get("name")]


def _load_core_properties(handle: zipfile.ZipFile) -> tuple[str, str]:
    if "docProps/core.xml" not in handle.namelist():
        return "", ""
    root = ET.fromstring(handle.read("docProps/core.xml"))
    created = _parse_iso_timestamp(_join_text(root.find("dcterms:created", XML_NS)))
    modified = _parse_iso_timestamp(_join_text(root.find("dcterms:modified", XML_NS)))
    return created, modified


def _first_sheet_path(handle: zipfile.ZipFile) -> str | None:
    candidates = sorted(name for name in handle.namelist() if name.startswith("xl/worksheets/") and name.endswith(".xml"))
    return candidates[0] if candidates else None


def _column_index(reference: str) -> int:
    letters = "".join(char for char in reference if char.isalpha()).upper()
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return max(0, value - 1)


def _decode_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.get("t", "")
    if cell_type == "inlineStr":
        return _join_text(cell.find("main:is", XML_NS))
    value_text = _join_text(cell.find("main:v", XML_NS))
    if cell_type == "s":
        try:
            return shared_strings[int(value_text)]
        except (ValueError, IndexError):
            return value_text
    return value_text


def _iter_sheet_rows(handle: zipfile.ZipFile, sheet_path: str, shared_strings: list[str], *, max_rows: int = 250) -> list[list[str]]:
    root = ET.fromstring(handle.read(sheet_path))
    rows: list[list[str]] = []
    for row in root.findall("main:sheetData/main:row", XML_NS):
        cells: dict[int, str] = {}
        max_index = -1
        for cell in row.findall("main:c", XML_NS):
            ref = cell.get("r", "")
            index = _column_index(ref)
            cells[index] = _decode_cell_value(cell, shared_strings)
            max_index = max(max_index, index)
        if max_index < 0:
            continue
        rows.append([cells.get(index, "") for index in range(max_index + 1)])
        if len(rows) >= max_rows:
            break
    return rows


def _excel_serial_to_timestamp(value: str) -> str:
    try:
        serial = float(value)
    except ValueError:
        return value
    if serial <= 59 or serial > 60000:
        return value
    return (EXCEL_EPOCH + timedelta(days=serial)).strftime("%Y-%m-%d %H:%M:%S")


def _normalize_date_cells(header: list[str], rows: Iterable[list[str]]) -> list[list[str]]:
    date_indexes = [index for index, field in enumerate(header) if any(token in field.lower() for token in ("date", "time", "timestamp"))]
    normalized: list[list[str]] = []
    for row in rows:
        adjusted = list(row)
        for index in date_indexes:
            if index < len(adjusted):
                adjusted[index] = _excel_serial_to_timestamp(adjusted[index].strip())
        normalized.append(adjusted)
    return normalized


def _special_workbook_family(path: Path, header: list[str], sheet_names: list[str], rows: list[list[str]]) -> str:
    name = path.name.lower()
    header_set = {cell.strip().lower() for cell in header}
    joined_values = " ".join(cell.strip().lower() for row in rows[:25] for cell in row if cell.strip())
    if "wealthsimple trade" in joined_values and "wealthsimple crypto" in joined_values and COINTRACKING_HEADERS.intersection(header_set):
        return "mixed_portfolio_workbook"
    if path.suffix.lower() == ".xlsx" and "cointracking_excel_import" in name:
        return "cointracking_import_workbook"
    return classify_file_family(path, header)


def inspect_workbook(path: Path) -> WorkbookInspection | None:
    if path.suffix.lower() != ".xlsx":
        return None
    try:
        with zipfile.ZipFile(path) as handle:
            shared_strings = _load_shared_strings(handle)
            sheet_names = _load_sheet_names(handle)
            created_at, modified_at = _load_core_properties(handle)
            sheet_path = _first_sheet_path(handle)
            if sheet_path is None:
                return None
            raw_rows = _iter_sheet_rows(handle, sheet_path, shared_strings)
    except (OSError, zipfile.BadZipFile, ET.ParseError):
        return None

    if not raw_rows:
        return WorkbookInspection(
            family="binary_evidence",
            header_preview="",
            data_rows="0",
            date_field="",
            min_timestamp="",
            max_timestamp="",
            timestamp_resolution="",
            timezone_mode="",
            timezone_value="",
            timezone_conflict="",
            scope_tokens=tuple(),
            export_timestamp=modified_at or created_at,
            workbook_sheet_names=" | ".join(sheet_names[:6]),
            workbook_created_at=created_at,
            workbook_modified_at=modified_at,
        )

    header, header_index = detect_header_from_rows(raw_rows)
    body_rows = raw_rows[header_index + 1 :] if header_index >= 0 else []
    normalized_rows = _normalize_date_cells(header, body_rows)
    analysis: TabularAnalysis = analyze_tabular_rows(
        filename=path.name,
        header=header,
        header_index=header_index,
        rows=normalized_rows,
    )
    family = _special_workbook_family(path, header, sheet_names, normalized_rows)
    row_dicts = [
        {header[index]: (row[index] if index < len(row) else "") for index in range(len(header))}
        for row in normalized_rows
        if any(cell.strip() for cell in row)
    ]
    scope_tokens = tuple(sorted(csv_scope_tokens(row_dicts)))
    export_timestamp = modified_at or created_at
    return WorkbookInspection(
        family=family,
        header_preview=" | ".join(header[:8]),
        data_rows=str(analysis.row_count),
        date_field=analysis.date_field,
        min_timestamp=analysis.min_timestamp,
        max_timestamp=analysis.max_timestamp,
        timestamp_resolution=analysis.timestamp_resolution,
        timezone_mode=analysis.timezone_mode,
        timezone_value=analysis.timezone_value,
        timezone_conflict=analysis.timezone_conflict,
        scope_tokens=scope_tokens,
        export_timestamp=export_timestamp,
        workbook_sheet_names=" | ".join(sheet_names[:6]),
        workbook_created_at=created_at,
        workbook_modified_at=modified_at,
    )
