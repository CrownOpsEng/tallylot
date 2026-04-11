"""Row-level validation helpers for manual balance submissions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.adapters.support import location_id_from_parts
from tallylot.domain.balances import BalanceReferenceKind, normalize_balance_kind
from tallylot.domain.temporal import TemporalPrecision

from .contracts import (
    BalanceReferenceSubmissionRow,
    BalanceSubmissionIssue,
    BalanceSnapshotSubmissionRow,
    LocationInventorySubmissionRow,
)
from .parsing import (
    SubmissionFieldContext,
    parse_submission_precision,
    parse_submission_quantity,
    parse_submission_reviewed_at,
    parse_submission_temporal_value,
)
from .schema import (
    BALANCE_REFERENCES_FILENAME,
    BALANCE_SNAPSHOTS_FILENAME,
    LOCATION_INVENTORY_FILENAME,
)


@dataclass(frozen=True)
class _ValidatedBalanceLikeRow:
    source: str
    account: str
    wallet: str
    instrument_id: str
    quantity: Decimal
    target_at: datetime
    target_precision: TemporalPrecision
    balance_kind: str
    notes: str


def validate_balance_rows(
    rows: list[tuple[int, dict[str, str]]],
    *,
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[BalanceSnapshotSubmissionRow]:
    parsed_rows: list[BalanceSnapshotSubmissionRow] = []
    for row_number, row in rows:
        base = _validate_balance_like_row(
            BALANCE_SNAPSHOTS_FILENAME,
            row_number,
            row,
            expected_source,
            issues,
        )
        if base is None:
            continue
        parsed_rows.append(
            BalanceSnapshotSubmissionRow(
                source=base.source,
                account=base.account,
                wallet=base.wallet,
                instrument_id=base.instrument_id,
                quantity=base.quantity,
                target_at=base.target_at,
                target_precision=base.target_precision,
                balance_kind=base.balance_kind,
                notes=base.notes,
            )
        )
    return parsed_rows


def validate_balance_reference_rows(
    rows: list[tuple[int, dict[str, str]]],
    *,
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[BalanceReferenceSubmissionRow]:
    parsed_rows: list[BalanceReferenceSubmissionRow] = []
    for row_number, row in rows:
        base = _validate_balance_like_row(
            BALANCE_REFERENCES_FILENAME,
            row_number,
            row,
            expected_source,
            issues,
        )
        reference_kind = row.get("reference_kind", "").strip()
        observed_at = row.get("observed_at", "").strip()
        observed_precision = row.get("observed_precision", "").strip()
        reviewed_by = row.get("reviewed_by", "").strip()
        reviewed_at = row.get("reviewed_at", "").strip()
        support_ref = row.get("support_ref", "").strip()
        row_valid = True
        for field_name, value in (
            ("reference_kind", reference_kind),
            ("observed_at", observed_at),
            ("observed_precision", observed_precision),
            ("reviewed_by", reviewed_by),
            ("reviewed_at", reviewed_at),
        ):
            if value:
                continue
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCE_REFERENCES_FILENAME,
                    row_number=str(row_number),
                    column_name=field_name,
                    issue_kind="missing_required_value",
                    message=(
                        f"balance_references.csv rows require a non-blank {field_name}."
                    ),
                )
            )
        normalized_kind: BalanceReferenceKind | None = None
        if reference_kind:
            try:
                normalized_kind = BalanceReferenceKind(reference_kind)
            except ValueError as exc:
                row_valid = False
                issues.append(
                    BalanceSubmissionIssue(
                        file_name=BALANCE_REFERENCES_FILENAME,
                        row_number=str(row_number),
                        column_name="reference_kind",
                        issue_kind="invalid_reference_kind",
                        message=str(exc),
                    )
                )
        if (
            normalized_kind is not None
            and normalized_kind is not BalanceReferenceKind.OPERATOR_ASSERTION
        ):
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCE_REFERENCES_FILENAME,
                    row_number=str(row_number),
                    column_name="reference_kind",
                    issue_kind="unsupported_reference_kind",
                    message=(
                        "Manual submission balance_references.csv rows must use "
                        "reference_kind operator_assertion."
                    ),
                )
            )
        parsed_observed_precision = _parse_precision(
            file_name=BALANCE_REFERENCES_FILENAME,
            row_number=row_number,
            column_name="observed_precision",
            raw_precision=observed_precision,
            issues=issues,
        )
        parsed_observed_at = parse_submission_temporal_value(
            context=SubmissionFieldContext(
                file_name=BALANCE_REFERENCES_FILENAME,
                row_number=row_number,
                column_name="observed_at",
                issues=issues,
            ),
            raw_value=observed_at,
            precision=parsed_observed_precision,
        )
        parsed_reviewed_at = _parse_reviewed_at(
            file_name=BALANCE_REFERENCES_FILENAME,
            row_number=row_number,
            raw_reviewed_at=reviewed_at,
            issues=issues,
        )
        if not row_valid or base is None or normalized_kind is None:
            continue
        if any(
            value is None
            for value in (
                parsed_observed_precision,
                parsed_observed_at,
                parsed_reviewed_at,
            )
        ):
            continue
        parsed_observed_precision_value = parsed_observed_precision
        parsed_observed_at_value = parsed_observed_at
        parsed_reviewed_at_value = parsed_reviewed_at
        assert parsed_observed_precision_value is not None
        assert parsed_observed_at_value is not None
        assert parsed_reviewed_at_value is not None
        parsed_rows.append(
            BalanceReferenceSubmissionRow(
                source=base.source,
                account=base.account,
                wallet=base.wallet,
                instrument_id=base.instrument_id,
                quantity=base.quantity,
                target_at=base.target_at,
                target_precision=base.target_precision,
                balance_kind=base.balance_kind,
                reference_kind=normalized_kind.value,
                observed_at=parsed_observed_at_value,
                observed_precision=parsed_observed_precision_value,
                support_ref=support_ref,
                reviewed_by=reviewed_by,
                reviewed_at=parsed_reviewed_at_value,
                notes=base.notes,
            )
        )
    return parsed_rows


def validate_location_inventory_rows(
    rows: list[tuple[int, dict[str, str]]],
    *,
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
            "target_at",
            "target_precision",
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
    quantity = _parse_quantity(
        file_name=file_name,
        row_number=row_number,
        raw_quantity=required["quantity"],
        issues=issues,
    )
    precision = _parse_precision(
        file_name=file_name,
        row_number=row_number,
        column_name="target_precision",
        raw_precision=required["target_precision"],
        issues=issues,
    )
    target_at = parse_submission_temporal_value(
        context=SubmissionFieldContext(
            file_name=file_name,
            row_number=row_number,
            column_name="target_at",
            issues=issues,
        ),
        raw_value=required["target_at"],
        precision=precision,
    )
    if required["balance_kind"]:
        normalize_balance_kind(required["balance_kind"])
    if not row_valid or quantity is None or precision is None or target_at is None:
        return None
    return _ValidatedBalanceLikeRow(
        source=required["source"],
        account=required["account"],
        wallet=required["wallet"],
        instrument_id=required["instrument_id"],
        quantity=quantity,
        target_at=target_at,
        target_precision=precision,
        balance_kind=normalize_balance_kind(required["balance_kind"]),
        notes=row.get("notes", "").strip(),
    )


def _parse_quantity(
    *,
    file_name: str,
    row_number: int,
    raw_quantity: str,
    issues: list[BalanceSubmissionIssue],
) -> Decimal | None:
    return parse_submission_quantity(
        file_name=file_name,
        row_number=row_number,
        raw_quantity=raw_quantity,
        issues=issues,
    )


def _parse_precision(
    *,
    file_name: str,
    row_number: int,
    column_name: str,
    raw_precision: str,
    issues: list[BalanceSubmissionIssue],
) -> TemporalPrecision | None:
    return parse_submission_precision(
        file_name=file_name,
        row_number=row_number,
        column_name=column_name,
        raw_precision=raw_precision,
        issues=issues,
    )


def _parse_reviewed_at(
    *,
    file_name: str,
    row_number: int,
    raw_reviewed_at: str,
    issues: list[BalanceSubmissionIssue],
) -> datetime | None:
    return parse_submission_reviewed_at(
        file_name=file_name,
        row_number=row_number,
        raw_reviewed_at=raw_reviewed_at,
        issues=issues,
    )
