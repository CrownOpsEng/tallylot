"""Validation for manual balance submission packages."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import InvalidOperation
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import location_id_from_parts
from tallylot.domain.checkpoints import normalize_balance_kind
from tallylot.domain.temporal import TemporalPrecision, parse_temporal_precision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value

from .contracts import (
    BalanceEvidenceSubmissionRow,
    BalanceSubmissionIssue,
    BalanceSubmissionRow,
    BalanceSubmissionValidationResult,
    LocationInventorySubmissionRow,
)
from .schema import (
    BALANCE_EVIDENCE_FILENAME,
    BALANCE_EVIDENCE_HEADER,
    BALANCES_FILENAME,
    BALANCES_HEADER,
    LOCATION_INVENTORY_FILENAME,
    LOCATION_INVENTORY_HEADER,
)


@dataclass(frozen=True)
class _ValidatedBalanceLikeRow:
    source: str
    account: str
    wallet: str
    instrument_id: str
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision
    balance_kind: str
    notes: str


def validate_balance_submission(
    submission_root: Path,
    *,
    expected_source: str,
) -> BalanceSubmissionValidationResult:
    issues: list[BalanceSubmissionIssue] = []
    balance_rows = _read_required_rows(
        submission_root / BALANCES_FILENAME,
        header=BALANCES_HEADER,
        issues=issues,
    )
    balance_evidence_rows = _read_required_rows(
        submission_root / BALANCE_EVIDENCE_FILENAME,
        header=BALANCE_EVIDENCE_HEADER,
        issues=issues,
    )
    location_inventory_rows = _read_optional_rows(
        submission_root / LOCATION_INVENTORY_FILENAME,
        header=LOCATION_INVENTORY_HEADER,
        issues=issues,
    )
    parsed_balances = _validate_balances(balance_rows, expected_source, issues)
    parsed_evidence = _validate_balance_evidence(
        balance_evidence_rows, expected_source, issues
    )
    parsed_location_inventory = _validate_location_inventory(
        location_inventory_rows, expected_source, issues
    )
    _collect_duplicates(
        BALANCES_FILENAME,
        balance_rows,
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
        ),
        issues,
    )
    _collect_duplicates(
        BALANCE_EVIDENCE_FILENAME,
        balance_evidence_rows,
        (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
            "evidence_ref",
        ),
        issues,
    )
    _collect_duplicates(
        LOCATION_INVENTORY_FILENAME,
        location_inventory_rows,
        (
            "source",
            "account",
            "wallet",
            "identifier_kind",
            "identifier_value",
            "network_scope",
        ),
        issues,
    )
    _collect_location_conflicts(parsed_location_inventory, issues)
    return BalanceSubmissionValidationResult(
        balance_rows=tuple(parsed_balances),
        balance_evidence_rows=tuple(parsed_evidence),
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


def _validate_balances(
    rows: list[tuple[int, dict[str, str]]],
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[BalanceSubmissionRow]:
    parsed_rows: list[BalanceSubmissionRow] = []
    for row_number, row in rows:
        base = _validate_balance_like_row(
            BALANCES_FILENAME,
            row_number,
            row,
            expected_source,
            issues,
        )
        if base is None:
            continue
        parsed_rows.append(
            BalanceSubmissionRow(
                source=base.source,
                account=base.account,
                wallet=base.wallet,
                instrument_id=base.instrument_id,
                quantity=base.quantity,
                as_of_at=base.as_of_at,
                as_of_precision=base.as_of_precision,
                balance_kind=base.balance_kind,
                notes=base.notes,
            )
        )
    return parsed_rows


def _validate_balance_evidence(
    rows: list[tuple[int, dict[str, str]]],
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[BalanceEvidenceSubmissionRow]:
    parsed_rows: list[BalanceEvidenceSubmissionRow] = []
    for row_number, row in rows:
        base = _validate_balance_like_row(
            BALANCE_EVIDENCE_FILENAME,
            row_number,
            row,
            expected_source,
            issues,
        )
        evidence_ref = row.get("evidence_ref", "").strip()
        if not evidence_ref:
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCE_EVIDENCE_FILENAME,
                    row_number=str(row_number),
                    column_name="evidence_ref",
                    issue_kind="missing_required_value",
                    message="Evidence rows require a non-blank evidence_ref.",
                )
            )
        if base is None or not evidence_ref:
            continue
        parsed_rows.append(
            BalanceEvidenceSubmissionRow(
                source=base.source,
                account=base.account,
                wallet=base.wallet,
                instrument_id=base.instrument_id,
                quantity=base.quantity,
                as_of_at=base.as_of_at,
                as_of_precision=base.as_of_precision,
                balance_kind=base.balance_kind,
                evidence_ref=evidence_ref,
                notes=base.notes,
            )
        )
    return parsed_rows


def _validate_location_inventory(
    rows: list[tuple[int, dict[str, str]]],
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[LocationInventorySubmissionRow]:
    parsed_rows: list[LocationInventorySubmissionRow] = []
    for row_number, row in rows:
        required = {
            field: row.get(field, "").strip()
            for field in (
                "source",
                "account",
                "wallet",
                "identifier_kind",
                "identifier_value",
                "confidence",
            )
        }
        row_valid = True
        for field_name, value in required.items():
            if value:
                continue
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=LOCATION_INVENTORY_FILENAME,
                    row_number=str(row_number),
                    column_name=field_name,
                    issue_kind="missing_required_value",
                    message=f"Location inventory rows require a non-blank {field_name}.",
                )
            )
        if required["source"] and required["source"] != expected_source:
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=LOCATION_INVENTORY_FILENAME,
                    row_number=str(row_number),
                    column_name="source",
                    issue_kind="source_mismatch",
                    message=(
                        f"Location inventory row source {required['source']!r} does not match "
                        f"submission source {expected_source!r}."
                    ),
                )
            )
        if row_valid:
            try:
                location_id_from_parts(
                    required["source"],
                    required["account"],
                    required["wallet"],
                )
            except ValueError as exc:
                row_valid = False
                issues.append(
                    BalanceSubmissionIssue(
                        file_name=LOCATION_INVENTORY_FILENAME,
                        row_number=str(row_number),
                        column_name="wallet",
                        issue_kind="invalid_location_parts",
                        message=str(exc),
                    )
                )
        if not row_valid:
            continue
        parsed_rows.append(
            LocationInventorySubmissionRow(
                source=required["source"],
                account=required["account"],
                wallet=required["wallet"],
                identifier_kind=required["identifier_kind"],
                identifier_value=required["identifier_value"],
                network_scope=row.get("network_scope", "").strip(),
                controller=row.get("controller", "").strip(),
                confidence=required["confidence"],
                notes=row.get("notes", "").strip(),
            )
        )
    return parsed_rows


def _validate_balance_like_row(
    file_name: str,
    row_number: int,
    row: dict[str, str],
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> _ValidatedBalanceLikeRow | None:
    required = {
        field: row.get(field, "").strip()
        for field in (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
        )
    }
    row_valid = True
    for field_name, value in required.items():
        if value:
            continue
        row_valid = False
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name=field_name,
                issue_kind="missing_required_value",
                message=f"{file_name} rows require a non-blank {field_name}.",
            )
        )
    if required["source"] and required["source"] != expected_source:
        row_valid = False
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name="source",
                issue_kind="source_mismatch",
                message=(
                    f"{file_name} row source {required['source']!r} does not match "
                    f"submission source {expected_source!r}."
                ),
            )
        )
    quantity = None
    if required["quantity"]:
        try:
            quantity = parse_decimal(required["quantity"])
        except (ArithmeticError, InvalidOperation, ValueError) as exc:
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=file_name,
                    row_number=str(row_number),
                    column_name="quantity",
                    issue_kind="invalid_decimal",
                    message=f"Could not parse quantity as Decimal: {exc}",
                )
            )
        if quantity is None:
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=file_name,
                    row_number=str(row_number),
                    column_name="quantity",
                    issue_kind="invalid_decimal",
                    message="Could not parse quantity as Decimal.",
                )
            )
    precision = None
    if required["as_of_precision"]:
        precision = parse_temporal_precision(required["as_of_precision"])
        if precision is None:
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=file_name,
                    row_number=str(row_number),
                    column_name="as_of_precision",
                    issue_kind="invalid_precision",
                    message=(
                        f"Unsupported as_of_precision {required['as_of_precision']!r}."
                    ),
                )
            )
    as_of_at = None
    if required["as_of_at"] and precision is not None:
        try:
            as_of_at = parse_temporal_value(required["as_of_at"], precision=precision)
        except ValueError as exc:
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=file_name,
                    row_number=str(row_number),
                    column_name="as_of_at",
                    issue_kind="invalid_timestamp",
                    message=str(exc),
                )
            )
    if required["balance_kind"]:
        normalize_balance_kind(required["balance_kind"])
    if not row_valid or quantity is None or precision is None or as_of_at is None:
        return None
    return _ValidatedBalanceLikeRow(
        source=required["source"],
        account=required["account"],
        wallet=required["wallet"],
        instrument_id=required["instrument_id"],
        quantity=quantity,
        as_of_at=as_of_at,
        as_of_precision=precision,
        balance_kind=normalize_balance_kind(required["balance_kind"]),
        notes=row.get("notes", "").strip(),
    )


def _collect_duplicates(
    file_name: str,
    rows: list[tuple[int, dict[str, str]]],
    fields: tuple[str, ...],
    issues: list[BalanceSubmissionIssue],
) -> None:
    seen: dict[tuple[str, ...], int] = {}
    for row_number, row in rows:
        key = tuple(row.get(field, "").strip() for field in fields)
        if not any(key):
            continue
        first_row = seen.get(key)
        if first_row is None:
            seen[key] = row_number
            continue
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name="",
                issue_kind="duplicate_row",
                message=(
                    f"Row duplicates the logical key first seen on row {first_row}."
                ),
            )
        )


def _collect_location_conflicts(
    rows: list[LocationInventorySubmissionRow],
    issues: list[BalanceSubmissionIssue],
) -> None:
    high_confidence_keys: dict[tuple[str, str, str], set[tuple[str, str, str]]] = {}
    for row in rows:
        if row.confidence.strip().lower() != "high":
            continue
        location_key = (row.source, row.account, row.wallet)
        identifier_key = (
            row.identifier_kind,
            row.identifier_value,
            row.network_scope,
        )
        high_confidence_keys.setdefault(location_key, set()).add(identifier_key)
    for source, account, wallet in sorted(high_confidence_keys):
        identifiers = high_confidence_keys[(source, account, wallet)]
        if len(identifiers) <= 1:
            continue
        issues.append(
            BalanceSubmissionIssue(
                file_name=LOCATION_INVENTORY_FILENAME,
                row_number="",
                column_name="confidence",
                issue_kind="conflicting_high_confidence_identity",
                message=(
                    "More than one high-confidence identity row maps to the same "
                    f"logical location {source}/{account}/{wallet}."
                ),
            )
        )
