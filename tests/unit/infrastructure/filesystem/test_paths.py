from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.infrastructure.filesystem import ensure_directory


def test_ensure_directory_creates_nested_path_and_returns_it(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "reports"

    returned = ensure_directory(path)

    assert returned == path
    assert path.is_dir()
