from __future__ import annotations

import contextlib
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from tests.support.helpers import read_dict_rows
import source_manifest


class SourceManifestTests(unittest.TestCase):
    def test_sha256sum_matches_hashlib(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.txt"
            path.write_text("hello manifest\n", encoding="utf-8")

            self.assertEqual(
                hashlib.sha256(b"hello manifest\n").hexdigest(),
                source_manifest.sha256sum(path),
            )

    def test_build_manifest_rows_ignores_support_files_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source" / "raw"
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

        self.assertEqual(["keep.csv", "nested/data.txt"], [row["filename"] for row in rows])
        self.assertEqual("8", str(rows[0]["size_bytes"]))
        self.assertEqual(hashlib.sha256(b"a,b\n1,2\n").hexdigest(), rows[0]["sha256"])
        self.assertEqual(hashlib.sha256(b"payload\n").hexdigest(), rows[1]["sha256"])

    def test_write_manifest_outputs_csv(self) -> None:
        rows = [{"filename": "keep.csv", "size_bytes": 7, "sha256": "abc"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "manifest.csv"
            source_manifest.write_manifest(output, rows)
            written_rows = read_dict_rows(output)

        self.assertEqual("keep.csv", written_rows[0]["filename"])
        self.assertEqual("7", written_rows[0]["size_bytes"])

    def test_build_manifest_rows_rejects_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "missing"
            output = Path(tmpdir) / "manifest.csv"

            with self.assertRaises(FileNotFoundError):
                source_manifest.build_manifest_rows(source_dir, output)

    def test_build_manifest_rows_rejects_non_raw_directory_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            output = Path(tmpdir) / "manifest.csv"

            with self.assertRaisesRegex(ValueError, "raw export folder"):
                source_manifest.build_manifest_rows(source_dir, output)

    def test_build_manifest_rows_allows_non_raw_directory_with_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            (source_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            output = Path(tmpdir) / "manifest.csv"

            rows = source_manifest.build_manifest_rows(source_dir, output, allow_non_raw_dir=True)

        self.assertEqual("payload.csv", rows[0]["filename"])

    def test_require_directory_rejects_non_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "file.txt"
            path.write_text("x", encoding="utf-8")
            with self.assertRaises(NotADirectoryError):
                source_manifest.require_directory(path, "Source directory")

    def test_parse_args_reads_expected_paths(self) -> None:
        args = source_manifest.parse_args(["--source-dir", "source", "--output", "manifest.csv"])

        self.assertEqual(Path("source"), args.source_dir)
        self.assertEqual(Path("manifest.csv"), args.output)
        self.assertFalse(args.allow_non_raw_dir)

    def test_main_writes_manifest_and_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source" / "raw"
            output = Path(tmpdir) / "manifest.csv"
            source_dir.mkdir(parents=True)
            (source_dir / "payload.csv").write_text("a,b\n1,2\n", encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = source_manifest.main(["--source-dir", str(source_dir), "--output", str(output)])

            rows = read_dict_rows(output)

        self.assertEqual(0, exit_code)
        self.assertEqual("payload.csv", rows[0]["filename"])
        self.assertIn("Wrote manifest with 1 file(s)", stdout.getvalue())
