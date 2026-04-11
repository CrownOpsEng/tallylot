"""Validation for manual balance submission packages."""

from __future__ import annotations

import csv
from pathlib import Path

from .consistency import (
    collect_balance_reference_mismatches,
    collect_duplicate_rows,
    collect_location_inventory_conflicts,
)
from .contracts import (
    BalanceSubmissionIssue,
    BalanceSubmissionValidationResult,
)
from .row_validation import (
    validate_balance_reference_rows,
    validate_balance_rows,
    validate_location_inventory_rows,
)
from .schema import (
    BALANCE_REFERENCES_FILENAME,
    BALANCE_REFERENCES_HEADER,
    BALANCE_SNAPSHOTS_FILENAME,
    BALANCE_SNAPSHOTS_HEADER,
    LOCATION_INVENTORY_FILENAME,
    LOCATION_INVENTORY_HEADER,
)


def validate_balance_submission(
    submission_root: Path,
    *,
    expected_source: str,
) -> BalanceSubmissionValidationResult:
    issues: list[BalanceSubmissionIssue] = []
    balance_rows = _read_required_rows(
        submission_root / BALANCE_SNAPSHOTS_FILENAME,
        header=BALANCE_SNAPSHOTS_HEADER,
        issues=issues,
    )
    balance_reference_rows = _read_required_rows(
        submission_root / BALANCE_REFERENCES_FILENAME,
        header=BALANCE_REFERENCES_HEADER,
        issues=issues,
    )
    location_inventory_rows = _read_optional_rows(
        submission_root / LOCATION_INVENTORY_FILENAME,
        header=LOCATION_INVENTORY_HEADER,
        issues=issues,
    )
    parsed_balances = validate_balance_rows(
        balance_rows,
        expected_source=expected_source,
        issues=issues,
    )
    parsed_references = validate_balance_reference_rows(
        balance_reference_rows,
        expected_source=expected_source,
        issues=issues,
    )
    parsed_location_inventory = validate_location_inventory_rows(
        location_inventory_rows,
        expected_source=expected_source,
        issues=issues,
    )
    collect_duplicate_rows(
        file_name=BALANCE_SNAPSHOTS_FILENAME,
        rows=balance_rows,
        fields=(
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "target_at",
            "target_precision",
            "balance_kind",
        ),
        issues=issues,
    )
    collect_duplicate_rows(
        file_name=BALANCE_REFERENCES_FILENAME,
        rows=balance_reference_rows,
        fields=(
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "target_at",
            "target_precision",
            "balance_kind",
        ),
        issues=issues,
    )
    collect_duplicate_rows(
        file_name=LOCATION_INVENTORY_FILENAME,
        rows=location_inventory_rows,
        fields=(
            "source",
            "account",
            "wallet",
            "identifier_kind",
            "identifier_value",
            "network_scope",
        ),
        issues=issues,
    )
    collect_location_inventory_conflicts(parsed_location_inventory, issues=issues)
    if not (
        _has_required_file_issue(issues, BALANCE_SNAPSHOTS_FILENAME)
        or _has_required_file_issue(issues, BALANCE_REFERENCES_FILENAME)
    ):
        collect_balance_reference_mismatches(
            tuple(parsed_balances),
            tuple(parsed_references),
            issues=issues,
        )
    return BalanceSubmissionValidationResult(
        balance_snapshot_rows=tuple(parsed_balances),
        balance_reference_rows=tuple(parsed_references),
        location_inventory_rows=tuple(parsed_location_inventory),
        issues=tuple(issues),
    )


def _read_required_rows(
    path: Path,
    *,
    header: tuple[str, ...],
    issues: list[BalanceSubmissionIssue],
) -> list[tuple[int, dict[str, str]]]:
    if not path.is_file():
        issues.append(
            BalanceSubmissionIssue(
                file_name=path.name,
                row_number="",
                column_name="",
                issue_kind="missing_required_file",
                message=f"Required submission file is missing: {path.name}",
            )
        )
        return []
    return _read_rows(path, header=header, issues=issues)


def _read_optional_rows(
    path: Path,
    *,
    header: tuple[str, ...],
    issues: list[BalanceSubmissionIssue],
) -> list[tuple[int, dict[str, str]]]:
    if not path.is_file():
        return []
    return _read_rows(path, header=header, issues=issues)


def _read_rows(
    path: Path,
    *,
    header: tuple[str, ...],
    issues: list[BalanceSubmissionIssue],
) -> list[tuple[int, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        actual_header = tuple(next(reader, ()))
    if actual_header != header:
        issues.append(
            BalanceSubmissionIssue(
                file_name=path.name,
                row_number="1",
                column_name="",
                issue_kind="invalid_header",
                message=(
                    f"Header mismatch for {path.name}. "
                    f"Expected {header} but found {actual_header}."
                ),
            )
        )
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        dict_reader = csv.DictReader(handle)
        return [
            (index, {key: value for key, value in row.items() if key is not None})
            for index, row in enumerate(dict_reader, start=2)
        ]


def _has_required_file_issue(
    issues: list[BalanceSubmissionIssue],
    file_name: str,
) -> bool:
    return any(
        issue.file_name == file_name
        and issue.issue_kind in {"missing_required_file", "invalid_header"}
        for issue in issues
    )
