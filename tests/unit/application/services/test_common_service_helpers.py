from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.services.common import ensure_directory, sha256sum


def test_sha256sum_hashes_file_contents(tmp_path: Path) -> None:
    path = tmp_path / "fixture.txt"
    path.write_text("crypto-reconciliation\n", encoding="utf-8")

    assert sha256sum(path) == "f2dac28b97116f7ef4ff40232dd22fc6bb0623a3978b824e4ca541a3548c0803"


def test_ensure_directory_creates_nested_path_and_returns_it(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "reports"

    returned = ensure_directory(path)

    assert returned == path
    assert path.is_dir()
