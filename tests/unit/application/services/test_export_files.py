from __future__ import annotations

from pathlib import Path

import pytest

from crypto_reconciliation.application.services.export_files import (
    find_matching_csv_files,
    find_required_csv_export,
    find_required_csv_exports,
)


def test_find_matching_csv_files_returns_sorted_csv_matches_only(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table B.csv").write_text("x\n", encoding="utf-8")
    (export_dir / "Trade Table A.csv").write_text("x\n", encoding="utf-8")
    (export_dir / "Trade Table.txt").write_text("x\n", encoding="utf-8")
    (export_dir / "Balance by Exchange.csv").write_text("x\n", encoding="utf-8")

    matches = find_matching_csv_files(export_dir, "Trade Table")

    assert [path.name for path in matches] == ["Trade Table A.csv", "Trade Table B.csv"]


def test_find_required_csv_export_rejects_missing_required_export(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="exactly one export"):
        find_required_csv_export(export_dir, "Trade Table")


def test_find_required_csv_export_rejects_ambiguous_match(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table A.csv").write_text("x\n", encoding="utf-8")
    (export_dir / "Trade Table B.csv").write_text("x\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Ambiguous export"):
        find_required_csv_export(export_dir, "Trade Table")


def test_find_required_csv_exports_returns_exact_mapping(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table.csv").write_text("x\n", encoding="utf-8")
    (export_dir / "Current Balance.csv").write_text("x\n", encoding="utf-8")

    resolved = find_required_csv_exports(export_dir, ("Trade Table", "Current Balance"))

    assert resolved == {
        "Trade Table": export_dir / "Trade Table.csv",
        "Current Balance": export_dir / "Current Balance.csv",
    }
