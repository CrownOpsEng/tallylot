from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.infrastructure.serialization.csv_io import read_rows, write_rows
from crypto_reconciliation.infrastructure.serialization.json_io import write_json


def test_read_and_write_csv_rows_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "round_trip.csv"
    rows = (
        {"alpha": "1", "beta": "two"},
        {"alpha": "3", "beta": "four"},
    )

    write_rows(path, ("alpha", "beta"), rows)

    assert read_rows(path) == list(rows)


def test_read_rows_accepts_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.csv"
    path.write_text("\ufeffalpha,beta\n1,two\n", encoding="utf-8")

    assert read_rows(path) == [{"alpha": "1", "beta": "two"}]


def test_write_rows_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "rows.csv"

    write_rows(path, ("alpha",), ({"alpha": "1"},))

    assert path.exists()


def test_write_json_creates_parent_directories_and_sorts_keys(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "payload.json"

    write_json(path, {"zeta": 2, "alpha": 1})

    assert path.exists()
    assert path.read_text(encoding="utf-8") == '{\n  "alpha": 1,\n  "zeta": 2\n}'
