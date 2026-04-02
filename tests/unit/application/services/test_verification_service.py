from __future__ import annotations

from pathlib import Path

import pytest

from crypto_reconciliation.application.services.verification import required_verification_paths


def test_required_verification_paths_rejects_missing_exports(tmp_path: Path) -> None:
    export_dir = tmp_path / "verification"
    export_dir.mkdir()
    (export_dir / "Validate Transactions.csv").write_text("Issue\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Missing required export 'Missing Transactions.csv'"):
        required_verification_paths(export_dir)


def test_required_verification_paths_rejects_non_directory_inputs(tmp_path: Path) -> None:
    export_file = tmp_path / "verification.csv"
    export_file.write_text("Issue\n", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="verification path is not a directory"):
        required_verification_paths(export_file)
