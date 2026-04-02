from __future__ import annotations

import contextlib
import io
from datetime import date
from pathlib import Path

import pytest

import round_scaffold
from tests.support.helpers import read_dict_rows


def test_validate_round_id_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        round_scaffold.validate_round_id("   ")


def test_validate_round_id_rejects_traversal() -> None:
    with pytest.raises(ValueError, match="single path segment"):
        round_scaffold.validate_round_id("../outside")


def test_validate_round_id_rejects_nested_path() -> None:
    with pytest.raises(ValueError, match="single path segment"):
        round_scaffold.validate_round_id("rounds/01")


def test_build_verification_readme_lists_default_exports() -> None:
    readme = round_scaffold.build_verification_readme("round_01", "baseline_repair", "shakepay")

    assert "- Validate Transactions" in readme
    assert "- Balance by Exchange" in readme
    assert "round_01" in readme


def test_scaffold_round_creates_readme_and_log_entry(tmp_path: Path) -> None:
    repo_root = tmp_path
    verification_dir, round_log_path = round_scaffold.scaffold_round(
        repo_root=repo_root,
        round_id="round_01",
        phase="baseline_repair",
        source="shakepay",
        today=date(2026, 3, 22),
    )

    assert (verification_dir / "README.md").exists()
    rows = read_dict_rows(round_log_path)
    assert len(rows) == 1
    assert rows[0]["round_id"] == "round_01"
    assert rows[0]["date"] == "2026-03-22"
    assert rows[0]["gate_result"] == "pending"
    assert rows[0]["goal"] == "Capture fresh verification exports after baseline repair"
    assert rows[0]["exports_captured"] == "02_working/verification/round_01"


def test_scaffold_round_is_idempotent_for_existing_round_id(tmp_path: Path) -> None:
    repo_root = tmp_path
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
    assert len(rows) == 1


def test_scaffold_round_preserves_existing_round_log_rows(tmp_path: Path) -> None:
    repo_root = tmp_path
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
    assert [row["round_id"] for row in rows] == ["round_00", "round_01"]
    assert rows[0]["goal"] == "Existing goal"
    assert rows[1]["goal"] == "Capture fresh verification exports after source import"


def test_scaffold_round_preserves_existing_readme(tmp_path: Path) -> None:
    repo_root = tmp_path
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

    assert readme_path.read_text(encoding="utf-8") == "custom notes\n"


def test_create_round_log_entry_uses_phase_specific_goal() -> None:
    entry = round_scaffold.create_round_log_entry(
        round_id="round_02",
        phase="post_import",
        source="kraken",
        verification_dir=Path("/repo/02_working/verification/round_02"),
        repo_root=Path("/repo"),
        today=date(2026, 3, 22),
    )

    assert entry["goal"] == "Capture fresh verification exports after source import"
    assert entry["exports_captured"] == "02_working/verification/round_02"


def test_parse_args_reads_expected_fields() -> None:
    args = round_scaffold.parse_args(
        ["--round-id", "round_01", "--phase", "baseline_repair", "--source", "shakepay"]
    )

    assert args.round_id == "round_01"
    assert args.phase == "baseline_repair"
    assert args.source == "shakepay"


def test_main_creates_round_and_prints_paths(tmp_path: Path) -> None:
    repo_root = tmp_path
    stdout = io.StringIO()

    with contextlib.redirect_stdout(stdout):
        exit_code = round_scaffold.main(
            ["--round-id", "round_01", "--phase", "baseline_repair", "--source", "shakepay"],
            repo_root=repo_root,
        )

    round_log_rows = read_dict_rows(repo_root / "05_outputs" / "logs" / "round_log.csv")
    readme_exists = (repo_root / "02_working" / "verification" / "round_01" / "README.md").exists()

    assert exit_code == 0
    assert readme_exists
    assert round_log_rows[0]["round_id"] == "round_01"
    assert "Verification folder:" in stdout.getvalue()
    assert "Round log:" in stdout.getvalue()
