from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "06_scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def read_dict_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run_script(
    script_name: str,
    *args: str,
    cwd: Path | None = None,
    scripts_dir: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    script = (scripts_dir or SCRIPTS_DIR) / script_name
    return subprocess.run(
        [sys.executable, str(script), *args],
        check=check,
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
    )


def copy_script_to_repo(script_name: str, repo_root: Path) -> Path:
    destination = repo_root / "06_scripts" / script_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPTS_DIR / script_name, destination)
    return destination


def _excel_column_name(index: int) -> str:
    value = index + 1
    letters = []
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


def write_minimal_xlsx(
    path: Path,
    rows: list[list[str]],
    *,
    sheet_name: str = "Sheet1",
    created_at: str | None = None,
    modified_at: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    shared_strings = sorted({cell for row in rows for cell in row if cell != ""})
    shared_index = {value: index for index, value in enumerate(shared_strings)}
    created = created_at or datetime(2022, 4, 5, 21, 34, 36).strftime("%Y-%m-%dT%H:%M:%SZ")
    modified = modified_at or created

    def cell_xml(row_index: int, column_index: int, value: str) -> str:
        ref = f"{_excel_column_name(column_index)}{row_index}"
        if value == "":
            return f'<c r="{ref}"/>'
        return f'<c r="{ref}" t="s"><v>{shared_index[value]}</v></c>'

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(cell_xml(row_index, column_index, value) for column_index, value in enumerate(row))
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')

    shared_strings_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">'
        + "".join(f"<si><t>{value}</t></si>" for value in shared_strings)
        + "</sst>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData>"
        "</worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
        "</Relationships>"
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        "</Types>"
    )
    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{modified}</dcterms:modified>'
        "</cp:coreProperties>"
    )

    with zipfile.ZipFile(path, "w") as handle:
        handle.writestr("[Content_Types].xml", content_types_xml)
        handle.writestr("_rels/.rels", root_rels_xml)
        handle.writestr("docProps/core.xml", core_xml)
        handle.writestr("xl/workbook.xml", workbook_xml)
        handle.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        handle.writestr("xl/sharedStrings.xml", shared_strings_xml)
        handle.writestr("xl/worksheets/sheet1.xml", sheet_xml)
