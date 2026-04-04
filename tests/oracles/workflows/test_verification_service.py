from __future__ import annotations

from pathlib import Path

import pytest

from tools.oracles.verification import required_verification_paths


def test_required_verification_paths_rejects_missing_exports(tmp_path: Path) -> None:
    export_dir = tmp_path / "verification"
    export_dir.mkdir()
    (export_dir / "Validate Transactions.csv").write_text("Issue\n", encoding="utf-8")

    with pytest.raises(
        FileNotFoundError, match="Missing required export 'Missing Transactions.csv'"
    ):
        required_verification_paths(export_dir)


def test_required_verification_paths_rejects_non_directory_inputs(
    tmp_path: Path,
) -> None:
    export_file = tmp_path / "verification.csv"
    export_file.write_text("Issue\n", encoding="utf-8")

    with pytest.raises(
        NotADirectoryError, match="verification path is not a directory"
    ):
        required_verification_paths(export_file)


def test_required_verification_paths_accepts_prefixed_export_filenames(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "verification"
    export_dir.mkdir()
    for filename in (
        "2026-03-22 CoinTracking - Validate Transactions (last sync 2023-08-05).csv",
        "2026-03-22 CoinTracking - Missing Transactions (last sync 2023-08-05).csv",
        "2026-03-22 CoinTracking - Duplicate Transactions (last sync 2023-08-05).csv",
        "2026-03-22 CoinTracking - Current Balance (last sync 2023-08-05).csv",
        "2026-03-22 CoinTracking - Balance by Exchange (last sync 2023-08-05).csv",
    ):
        (export_dir / filename).write_text("Issue\n", encoding="utf-8")

    resolved = required_verification_paths(export_dir)

    assert resolved["validate_transactions"].name.startswith(
        "2026-03-22 CoinTracking - Validate Transactions"
    )


def test_required_verification_paths_prefers_non_strict_missing_transactions_export(
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "verification"
    export_dir.mkdir()
    for filename in (
        "CoinTracking - Validate Transactions.csv",
        "CoinTracking - Missing Transactions.csv",
        "CoinTracking - Missing Transactions - Strict.csv",
        "CoinTracking - Duplicate Transactions.csv",
        "CoinTracking - Current Balance.csv",
        "CoinTracking - Balance by Exchange.csv",
    ):
        (export_dir / filename).write_text("Issue\n", encoding="utf-8")

    resolved = required_verification_paths(export_dir)

    assert (
        resolved["missing_transactions"].name
        == "CoinTracking - Missing Transactions.csv"
    )
