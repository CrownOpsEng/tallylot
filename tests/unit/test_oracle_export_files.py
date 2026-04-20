from __future__ import annotations

from pathlib import Path

import pytest

from tools.oracles.export_files import (
    find_matching_csv_files,
    find_required_csv_export,
    find_required_csv_exports,
)


def test_find_matching_csv_files_returns_sorted_csv_matches_only(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "b Trade Table.csv").write_text("x\n", encoding="utf-8")
    (export_dir / "a trade table.csv").write_text("x\n", encoding="utf-8")
    (export_dir / "Trade Table.txt").write_text("x\n", encoding="utf-8")

    matches = find_matching_csv_files(export_dir, "Trade Table")

    assert [path.name for path in matches] == ["a trade table.csv", "b Trade Table.csv"]


def test_find_required_csv_export_rejects_missing_required_export(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError, match="expected exactly one export containing"
    ):
        find_required_csv_export(tmp_path, "Trade Table")


def test_find_required_csv_export_rejects_ambiguous_match(tmp_path: Path) -> None:
    (tmp_path / "Trade Table A.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "Trade Table B.csv").write_text("x\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Ambiguous export containing"):
        find_required_csv_export(tmp_path, "Trade Table")


def test_find_required_csv_exports_returns_exact_mapping(tmp_path: Path) -> None:
    (tmp_path / "Trade Table.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "Current Balance.csv").write_text("x\n", encoding="utf-8")

    exports = find_required_csv_exports(tmp_path, ("Trade Table", "Current Balance"))

    assert exports == {
        "Trade Table": tmp_path / "Trade Table.csv",
        "Current Balance": tmp_path / "Current Balance.csv",
    }
