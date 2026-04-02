from __future__ import annotations

from pathlib import Path

import pytest

from tools.oracles.cointracking.baseline_exports import find_required_baseline_exports, match_baseline_exports


def test_match_baseline_exports_returns_zero_without_required_files(tmp_path: Path) -> None:
    assert match_baseline_exports(tmp_path) == 0


def test_match_baseline_exports_scores_partial_coverage(tmp_path: Path) -> None:
    for filename in ("Trade Table.csv", "Current Balance.csv", "Balance by Exchange.csv"):
        (tmp_path / filename).write_text("x\n", encoding="utf-8")

    assert match_baseline_exports(tmp_path) == 50


def test_find_required_baseline_exports_rejects_missing_files(tmp_path: Path) -> None:
    (tmp_path / "Trade Table.csv").write_text("x\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="expected exactly one export containing"):
        find_required_baseline_exports(tmp_path)


def test_find_required_baseline_exports_rejects_ambiguous_files(tmp_path: Path) -> None:
    for filename in (
        "Trade Table.csv",
        "Current Balance.csv",
        "Balance by Exchange.csv",
        "Validate Transactions.csv",
        "Missing Transactions.csv",
        "Duplicate Transactions.csv",
        "Duplicate Transactions Copy.csv",
    ):
        (tmp_path / filename).write_text("x\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Ambiguous export containing"):
        find_required_baseline_exports(tmp_path)
