"""CoinTracking candidate validation helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_reconciliation.domain.models import IssueRecord
from crypto_reconciliation.domain.value_objects import parse_timestamp
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

from .schema import COINTRACKING_HEADER


def match_candidate(candidate_path: Path, artifacts: ArtifactStorePort) -> int:
    try:
        header = tuple(artifacts.read_rows(candidate_path)[0].keys())
    except (FileNotFoundError, IndexError, KeyError):
        return 0
    return 100 if header == COINTRACKING_HEADER else 0


def candidate_validation_issues(candidate_path: Path) -> tuple[list[IssueRecord], int, list[dict[str, str]]]:
    with candidate_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        issues: list[IssueRecord] = []
        if header != COINTRACKING_HEADER:
            issues.append(
                IssueRecord(
                    issue_id=f"{candidate_path.name}:schema",
                    source="batch_screen",
                    adapter_id="cointracking_csv",
                    severity="high",
                    kind="invalid_schema",
                    message="The candidate file does not match the CoinTracking CSV header.",
                    raw_file=candidate_path.name,
                )
            )
            return issues, 0, []

        rows = list(reader)
    valid_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        date_value = (row.get("Date") or "").strip()
        tx_id = (row.get("Tx-ID") or "").strip()
        if not date_value:
            issues.append(issue(candidate_path, index, "missing_date", "Candidate rows must include Date."))
            continue
        if not tx_id:
            issues.append(issue(candidate_path, index, "missing_tx_id", "Candidate rows must include Tx-ID."))
            continue
        try:
            parse_timestamp(date_value)
        except ValueError:
            issues.append(
                issue(
                    candidate_path,
                    index,
                    "invalid_date",
                    f"Unsupported Date value: {date_value!r}.",
                )
            )
            continue
        valid_rows.append(row)
    return issues, len(rows), valid_rows


def issue(candidate_path: Path, row_ref: int, kind: str, message: str) -> IssueRecord:
    return IssueRecord(
        issue_id=f"{candidate_path.name}:{row_ref}:{kind}",
        source="batch_screen",
        adapter_id="cointracking_csv",
        severity="high",
        kind=kind,
        message=message,
        raw_file=candidate_path.name,
        raw_row_ref=str(row_ref),
    )
