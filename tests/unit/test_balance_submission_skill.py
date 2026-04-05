from __future__ import annotations

import json
import subprocess
from pathlib import Path

from repo_support.paths import repo_root
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_balance_submission_skill_runner_resolves_repo_root_and_inspects_missing_values(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "manual-source"

    result = subprocess.run(
        (
            "python3",
            str(
                repo_root()
                / ".agents/skills/balance-submission-operations/scripts/balance_submission_operations.py"
            ),
            "inspect",
            "--source",
            "manual-source",
            "--submission-root",
            str(submission_root),
        ),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["submission_root"] == str(submission_root)
    assert payload["ready_for_submit"] is False
    assert payload["issue_count"] >= 2
    assert any(
        issue["issue_kind"] == "missing_required_file" for issue in payload["issues"]
    )


def test_balance_submission_skill_run_mode_does_not_guess_missing_values(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "manual-source"
    output_root = tmp_path / "normalized" / "manual-source"

    result = subprocess.run(
        (
            "python3",
            ".agents/skills/balance-submission-operations/scripts/balance_submission_operations.py",
            "run",
            "--source",
            "manual-source",
            "--submission-root",
            str(submission_root),
            "--output-root",
            str(output_root),
        ),
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["blocked"] is True
    assert payload["stage"] == "inspect"
    assert payload["ready_for_submit"] is False
    assert not (output_root / "balances.csv").exists()


def test_balance_submission_skill_submit_writes_runtime_artifacts(
    tmp_path: Path,
) -> None:
    submission_root = tmp_path / "submission" / "manual-source"
    output_root = tmp_path / "normalized" / "manual-source"
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        submission_root / "balances.csv",
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
            "notes",
        ),
        (
            {
                "source": "manual-source",
                "account": "primary",
                "wallet": "primary",
                "instrument_id": "symbol:BTC",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "notes": "",
            },
        ),
    )
    artifacts.write_rows(
        submission_root / "balance_evidence.csv",
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
            "evidence_ref",
            "notes",
        ),
        (
            {
                "source": "manual-source",
                "account": "primary",
                "wallet": "primary",
                "instrument_id": "symbol:BTC",
                "quantity": "1.25",
                "as_of_at": "2026-03-23",
                "as_of_precision": "date",
                "balance_kind": "available",
                "evidence_ref": "manual-note:test",
                "notes": "",
            },
        ),
    )

    result = subprocess.run(
        (
            "python3",
            ".agents/skills/balance-submission-operations/scripts/balance_submission_operations.py",
            "submit",
            "--source",
            "manual-source",
            "--submission-root",
            str(submission_root),
            "--output-root",
            str(output_root),
        ),
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["blocked"] is False
    assert payload["summary_path"] == str(
        output_root / "balance_submission_summary.json"
    )
    assert (output_root / "balances.csv").exists()
