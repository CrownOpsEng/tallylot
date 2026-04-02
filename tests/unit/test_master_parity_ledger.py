from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = REPO_ROOT / "docs" / "MASTER_PARITY_LEDGER.md"
DOC_PATHS = [
    REPO_ROOT / "README.md",
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
    *sorted((REPO_ROOT / ".claude").rglob("*.md")),
]
FAMILY_HEADER_PATTERN = re.compile(r"^## `(tests/.+?\.py)`$")
LEGACY_TEST_COUNT_PATTERN = re.compile(r"^- Legacy tests: (\d+)$")
PROOF_TYPE_VALUES = frozenset({"ported-direct", "superseded-direct"})
TOTALS_KEYS = (
    "Legacy families on `master`",
    "Tracked family sections",
    "Tracked legacy behaviors",
    "`ported-direct` behaviors",
    "`superseded-direct` behaviors",
)


@dataclass(frozen=True)
class LedgerRow:
    legacy_family: str
    behavior_identifier: str
    proof_type: str
    proof_paths: tuple[str, ...]


@dataclass(frozen=True)
class LedgerSection:
    family: str
    legacy_test_count: int
    rows: tuple[LedgerRow, ...]


def _master_legacy_families() -> set[str]:
    result = subprocess.run(
        ("git", "ls-tree", "-r", "--name-only", "master", "tests"),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        line
        for line in result.stdout.splitlines()
        if line.startswith("tests/") and line.endswith(".py") and Path(line).name.startswith("test_")
    }


def _parse_ledger_sections() -> dict[str, LedgerSection]:
    text = LEDGER_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections: dict[str, LedgerSection] = {}
    index = 0
    while index < len(lines):
        header_match = FAMILY_HEADER_PATTERN.match(lines[index])
        if header_match is None:
            index += 1
            continue
        family = header_match.group(1)
        index += 1
        legacy_test_count: int | None = None
        rows: list[LedgerRow] = []
        while index < len(lines):
            if FAMILY_HEADER_PATTERN.match(lines[index]) is not None:
                break
            count_match = LEGACY_TEST_COUNT_PATTERN.match(lines[index])
            if count_match is not None:
                legacy_test_count = int(count_match.group(1))
            if lines[index].startswith("| `tests/"):
                cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
                assert len(cells) == 5, f"unexpected ledger row shape: {lines[index]!r}"
                proof_paths = tuple(re.findall(r"`([^`]+)`", cells[3]))
                rows.append(
                    LedgerRow(
                        legacy_family=cells[0].strip("`"),
                        behavior_identifier=cells[1].strip("`"),
                        proof_type=cells[2].strip("`"),
                        proof_paths=proof_paths,
                    )
                )
            index += 1
        assert legacy_test_count is not None, f"missing legacy test count for {family}"
        sections[family] = LedgerSection(
            family=family,
            legacy_test_count=legacy_test_count,
            rows=tuple(rows),
        )
    return sections


def _parse_totals() -> dict[str, int]:
    text = LEDGER_PATH.read_text(encoding="utf-8")
    totals: dict[str, int] = {}
    in_totals = False
    for line in text.splitlines():
        if line == "## Totals":
            in_totals = True
            continue
        if in_totals and line.startswith("## "):
            break
        if not in_totals or not line.startswith("| ") or "----" in line or "Count" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        totals[cells[0]] = int(cells[1])
    return totals


def test_master_legacy_family_set_matches_behavior_ledger_sections() -> None:
    assert _parse_ledger_sections().keys() == _master_legacy_families()


def test_each_legacy_family_has_behavior_rows_with_unique_identifiers() -> None:
    for section in _parse_ledger_sections().values():
        assert section.rows, f"{section.family} has no behavior rows"
        assert section.legacy_test_count == len(section.rows), (
            f"{section.family} expected {section.legacy_test_count} behavior rows but found {len(section.rows)}"
        )
        identifiers = [row.behavior_identifier for row in section.rows]
        assert len(identifiers) == len(set(identifiers)), f"{section.family} has duplicate behavior identifiers"


def test_behavior_rows_match_their_family_and_cite_existing_proof_paths() -> None:
    for section in _parse_ledger_sections().values():
        for row in section.rows:
            assert row.legacy_family == section.family
            assert row.proof_type in PROOF_TYPE_VALUES
            assert row.proof_paths, f"{section.family}::{row.behavior_identifier} has no proof paths"
            for proof_path in row.proof_paths:
                assert (REPO_ROOT / proof_path).exists(), (
                    f"{section.family}::{row.behavior_identifier} cites missing proof path {proof_path}"
                )


def test_ledger_totals_are_derived_from_behavior_rows() -> None:
    totals = _parse_totals()
    assert tuple(totals) == TOTALS_KEYS
    sections = _parse_ledger_sections()
    behavior_rows = [row for section in sections.values() for row in section.rows]
    ported = sum(1 for row in behavior_rows if row.proof_type == "ported-direct")
    superseded = sum(1 for row in behavior_rows if row.proof_type == "superseded-direct")
    assert totals == {
        "Legacy families on `master`": len(_master_legacy_families()),
        "Tracked family sections": len(sections),
        "Tracked legacy behaviors": len(behavior_rows),
        "`ported-direct` behaviors": ported,
        "`superseded-direct` behaviors": superseded,
    }


def test_retired_master_parity_matrix_is_absent_and_undocumented() -> None:
    assert not (REPO_ROOT / "docs" / "MASTER_TEST_PARITY_MATRIX.md").exists()
    for path in DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        assert "MASTER_TEST_PARITY_MATRIX.md" not in text, f"{path} still documents the retired parity matrix"
