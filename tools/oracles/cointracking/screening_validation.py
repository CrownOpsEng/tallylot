"""CoinTracking candidate validation helpers."""

from __future__ import annotations

from pathlib import Path

from tallylot.domain.issues import IssueRecord
from tallylot.domain.value_objects import parse_timestamp
from tallylot.ports.artifacts import ArtifactStorePort

from .schema import COINTRACKING_HEADER
from .screening_columns import cell, load_cointracking_rows


def match_candidate(candidate_path: Path, artifacts: ArtifactStorePort) -> int:
    del artifacts
    try:
        load_cointracking_rows(candidate_path)
    except (FileNotFoundError, ValueError):
        return 0
    return 100


def candidate_validation_issues(
    candidate_path: Path,
) -> tuple[list[IssueRecord], int, list[dict[str, str]]]:
    issues: list[IssueRecord] = []
    try:
        _, rows, columns = load_cointracking_rows(candidate_path)
    except ValueError:
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
    valid_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        date_value = cell(row, columns["date"])
        tx_id = cell(row, columns["tx_id"])
        if not date_value:
            issues.append(
                issue(
                    candidate_path,
                    index,
                    "missing_date",
                    "Candidate rows must include Date.",
                )
            )
            continue
        if not tx_id:
            issues.append(
                issue(
                    candidate_path,
                    index,
                    "missing_tx_id",
                    "Candidate rows must include Tx-ID.",
                )
            )
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
        valid_rows.append(_canonical_candidate_row(row, columns))
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


def _canonical_candidate_row(
    row: list[str], columns: dict[str, int | None]
) -> dict[str, str]:
    return {
        header_name: cell(row, column_index)
        for header_name, column_index in zip(
            COINTRACKING_HEADER,
            (
                columns["type"],
                columns["buy"],
                columns["buy_currency"],
                columns["sell"],
                columns["sell_currency"],
                columns["fee"],
                columns["fee_currency"],
                columns["exchange"],
                columns["group"],
                columns["comment"],
                columns["date"],
                columns["tx_id"],
            ),
            strict=True,
        )
    }
