#!/usr/bin/env python3

"""Create a verification folder and seed the round log."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Sequence

from script_common import DEFAULT_VERIFICATION_EXPORTS, read_csv_rows, write_csv_rows


ROUND_LOG_FIELDS = [
    "round_id",
    "phase",
    "source",
    "date",
    "goal",
    "cointracking_change",
    "exports_captured",
    "issues_opened_or_closed",
    "gate_result",
    "next_action",
]


def validate_round_id(round_id: str) -> str:
    if not round_id.strip():
        raise ValueError("round_id must not be empty")
    round_path = Path(round_id)
    if round_path.name != round_id or any(part == ".." for part in round_path.parts):
        raise ValueError("round_id must be a single path segment without traversal")
    return round_id


def build_verification_readme(round_id: str, phase: str, source: str) -> str:
    expected_exports = [f"- {export_name}" for export_name in DEFAULT_VERIFICATION_EXPORTS]
    return "\n".join(
        [
            "# Verification Round",
            "",
            f"- round_id: `{round_id}`",
            f"- phase: `{phase}`",
            f"- source: `{source}`",
            "",
            "Expected default export set:",
            *expected_exports,
            "",
            "Add Trade Table, Roll Forward, or Double-entry only when needed.",
            "",
        ]
    )


def ensure_round_log(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        write_csv_rows(path, ROUND_LOG_FIELDS, [])
        return []

    return read_csv_rows(path)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    write_csv_rows(path, ROUND_LOG_FIELDS, rows)


def create_round_log_entry(
    round_id: str,
    phase: str,
    source: str,
    verification_dir: Path,
    repo_root: Path,
    today: date,
) -> dict[str, str]:
    return {
        "round_id": round_id,
        "phase": phase,
        "source": source,
        "date": today.isoformat(),
        "goal": (
            "Capture fresh verification exports after baseline repair"
            if phase == "baseline_repair"
            else "Capture fresh verification exports after source import"
        ),
        "cointracking_change": "",
        "exports_captured": str(verification_dir.relative_to(repo_root)),
        "issues_opened_or_closed": "",
        "gate_result": "pending",
        "next_action": "Populate exports_captured details and update gate_result after verification.",
    }


def scaffold_round(
    repo_root: Path,
    round_id: str,
    phase: str,
    source: str,
    *,
    today: date | None = None,
) -> tuple[Path, Path]:
    repo_root = repo_root.resolve()
    round_id = validate_round_id(round_id)
    today = today or date.today()
    verification_dir = repo_root / "02_working" / "verification" / round_id
    verification_dir.mkdir(parents=True, exist_ok=True)

    readme_path = verification_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(build_verification_readme(round_id, phase, source), encoding="utf-8")

    round_log_path = repo_root / "05_outputs" / "logs" / "round_log.csv"
    rows = ensure_round_log(round_log_path)
    if not any(row["round_id"] == round_id for row in rows):
        rows.append(create_round_log_entry(round_id, phase, source, verification_dir, repo_root, today))
        write_rows(round_log_path, rows)
    return verification_dir, round_log_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-id", required=True)
    parser.add_argument("--phase", required=True, choices=["baseline_repair", "post_import"])
    parser.add_argument("--source", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, *, repo_root: Path | None = None) -> int:
    args = parse_args(argv)
    repo_root = repo_root or Path(__file__).resolve().parent.parent
    verification_dir, round_log_path = scaffold_round(
        repo_root=repo_root,
        round_id=args.round_id,
        phase=args.phase,
        source=args.source,
    )

    print(f"Verification folder: {verification_dir}")
    print(f"Round log: {round_log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
