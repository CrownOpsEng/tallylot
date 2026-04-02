from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tests.support.helpers import read_dict_rows
import round_scaffold


class RoundScaffoldTests(unittest.TestCase):
    def test_validate_round_id_rejects_empty_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            round_scaffold.validate_round_id("   ")

    def test_validate_round_id_rejects_traversal(self) -> None:
        with self.assertRaisesRegex(ValueError, "single path segment"):
            round_scaffold.validate_round_id("../outside")

    def test_validate_round_id_rejects_nested_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "single path segment"):
            round_scaffold.validate_round_id("rounds/01")

    def test_build_verification_readme_lists_default_exports(self) -> None:
        readme = round_scaffold.build_verification_readme("round_01", "baseline_repair", "shakepay")
        self.assertIn("- Validate Transactions", readme)
        self.assertIn("- Balance by Exchange", readme)
        self.assertIn("round_01", readme)

    def test_scaffold_round_creates_readme_and_log_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            verification_dir, round_log_path = round_scaffold.scaffold_round(
                repo_root=repo_root,
                round_id="round_01",
                phase="baseline_repair",
                source="shakepay",
                today=date(2026, 3, 22),
            )

            self.assertTrue((verification_dir / "README.md").exists())
            rows = read_dict_rows(round_log_path)

        self.assertEqual(1, len(rows))
        self.assertEqual("round_01", rows[0]["round_id"])
        self.assertEqual("2026-03-22", rows[0]["date"])
        self.assertEqual("pending", rows[0]["gate_result"])
        self.assertEqual("Capture fresh verification exports after baseline repair", rows[0]["goal"])
        self.assertEqual("02_working/verification/round_01", rows[0]["exports_captured"])

    def test_scaffold_round_is_idempotent_for_existing_round_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            kwargs = {
                "repo_root": repo_root,
                "round_id": "round_01",
                "phase": "post_import",
                "source": "shakepay",
                "today": date(2026, 3, 22),
            }

            round_scaffold.scaffold_round(**kwargs)
            round_scaffold.scaffold_round(**kwargs)

            rows = read_dict_rows(repo_root / "05_outputs" / "logs" / "round_log.csv")

        self.assertEqual(1, len(rows))

    def test_scaffold_round_preserves_existing_round_log_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            round_log_path = repo_root / "05_outputs" / "logs" / "round_log.csv"
            round_log_path.parent.mkdir(parents=True)
            round_log_path.write_text(
                (
                    "round_id,phase,source,date,goal,cointracking_change,exports_captured,"
                    "issues_opened_or_closed,gate_result,next_action\n"
                    "round_00,baseline_repair,cointracking,2026-03-21,Existing goal,,"
                    "02_working/verification/round_00,,pass,Done\n"
                ),
                encoding="utf-8",
            )

            round_scaffold.scaffold_round(
                repo_root=repo_root,
                round_id="round_01",
                phase="post_import",
                source="shakepay",
                today=date(2026, 3, 22),
            )

            rows = read_dict_rows(round_log_path)

        self.assertEqual(["round_00", "round_01"], [row["round_id"] for row in rows])
        self.assertEqual("Existing goal", rows[0]["goal"])
        self.assertEqual("Capture fresh verification exports after source import", rows[1]["goal"])

    def test_scaffold_round_preserves_existing_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            verification_dir = repo_root / "02_working" / "verification" / "round_01"
            verification_dir.mkdir(parents=True)
            readme_path = verification_dir / "README.md"
            readme_path.write_text("custom notes\n", encoding="utf-8")

            round_scaffold.scaffold_round(
                repo_root=repo_root,
                round_id="round_01",
                phase="baseline_repair",
                source="shakepay",
                today=date(2026, 3, 22),
            )

            readme_text = readme_path.read_text(encoding="utf-8")

        self.assertEqual("custom notes\n", readme_text)

    def test_create_round_log_entry_uses_phase_specific_goal(self) -> None:
        entry = round_scaffold.create_round_log_entry(
            round_id="round_02",
            phase="post_import",
            source="kraken",
            verification_dir=Path("/repo/02_working/verification/round_02"),
            repo_root=Path("/repo"),
            today=date(2026, 3, 22),
        )
        self.assertEqual("Capture fresh verification exports after source import", entry["goal"])
        self.assertEqual("02_working/verification/round_02", entry["exports_captured"])

    def test_parse_args_reads_expected_fields(self) -> None:
        args = round_scaffold.parse_args(
            ["--round-id", "round_01", "--phase", "baseline_repair", "--source", "shakepay"]
        )

        self.assertEqual("round_01", args.round_id)
        self.assertEqual("baseline_repair", args.phase)
        self.assertEqual("shakepay", args.source)

    def test_main_creates_round_and_prints_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = round_scaffold.main(
                    ["--round-id", "round_01", "--phase", "baseline_repair", "--source", "shakepay"],
                    repo_root=repo_root,
                )

            round_log_rows = read_dict_rows(repo_root / "05_outputs" / "logs" / "round_log.csv")
            readme_exists = (repo_root / "02_working" / "verification" / "round_01" / "README.md").exists()

        self.assertEqual(0, exit_code)
        self.assertTrue(readme_exists)
        self.assertEqual("round_01", round_log_rows[0]["round_id"])
        self.assertIn("Verification folder:", stdout.getvalue())
        self.assertIn("Round log:", stdout.getvalue())
