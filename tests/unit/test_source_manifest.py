from __future__ import annotations

import contextlib
import hashlib
import io
from pathlib import Path

import pytest

import source_manifest
from tests.support.helpers import read_dict_rows


def test_sha256sum_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("hello manifest\n", encoding="utf-8")

    assert source_manifest.sha256sum(path) == hashlib.sha256(b"hello manifest\n").hexdigest()


def test_build_manifest_rows_ignores_support_files_and_output(tmp_path: Path) -> None:
    source_dir = tmp_path / "source" / "raw"
    source_dir.mkdir(parents=True)
    (source_dir / "README.md").write_text("ignore me\n", encoding="utf-8")
    (source_dir / ".gitkeep").write_text("", encoding="utf-8")
    (source_dir / "keep.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    nested = source_dir / "nested"
    nested.mkdir()
    (nested / "data.txt").write_text("payload\n", encoding="utf-8")
    output = source_dir / "manifest.csv"
    output.write_text("stale manifest\n", encoding="utf-8")

    rows = source_manifest.build_manifest_rows(source_dir, output)

    assert [row["filename"] for row in rows] == ["keep.csv", "nested/data.txt"]
    assert str(rows[0]["size_bytes"]) == "8"
    assert rows[0]["sha256"] == hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    assert rows[1]["sha256"] == hashlib.sha256(b"payload\n").hexdigest()


def test_write_manifest_outputs_csv(tmp_path: Path) -> None:
    rows = [{"filename": "keep.csv", "size_bytes": 7, "sha256": "abc"}]
    output = tmp_path / "manifest.csv"

    source_manifest.write_manifest(output, rows)
    written_rows = read_dict_rows(output)

    assert written_rows[0]["filename"] == "keep.csv"
    assert written_rows[0]["size_bytes"] == "7"


def test_build_manifest_rows_rejects_missing_directory(tmp_path: Path) -> None:
    source_dir = tmp_path / "missing"
    output = tmp_path / "manifest.csv"

    with pytest.raises(FileNotFoundError):
        source_manifest.build_manifest_rows(source_dir, output)


def test_build_manifest_rows_accepts_capture_directory(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    output = tmp_path / "manifest.csv"

    rows = source_manifest.build_manifest_rows(source_dir, output)

    assert rows[0]["filename"] == "payload.csv"


def test_require_directory_rejects_non_directory(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("x", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        source_manifest.require_directory(path, "Source directory")


def test_parse_args_reads_expected_paths() -> None:
    args = source_manifest.parse_args(["--source-dir", "source", "--output", "manifest.csv"])

    assert args.source_dir == Path("source")
    assert args.output == Path("manifest.csv")


def test_main_writes_manifest_and_prints_summary(tmp_path: Path) -> None:
    source_dir = tmp_path / "source" / "raw"
    output = tmp_path / "manifest.csv"
    source_dir.mkdir(parents=True)
    (source_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = source_manifest.main(["--source-dir", str(source_dir), "--output", str(output)])

    rows = read_dict_rows(output)

    assert exit_code == 0
    assert rows[0]["filename"] == "payload.csv"
    assert "Wrote manifest with 1 file(s)" in stdout.getvalue()
