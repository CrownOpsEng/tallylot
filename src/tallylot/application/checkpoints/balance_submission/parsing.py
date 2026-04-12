"""Shared parsing helpers for manual balance submission validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation

from tallylot.domain.temporal import TemporalPrecision, parse_temporal_precision
from tallylot.domain.value_objects import (
    parse_decimal,
    parse_temporal_value,
    parse_timestamp,
)

from .contracts import BalanceSubmissionIssue


@dataclass(frozen=True)
class SubmissionFieldContext:
    file_name: str
    row_number: int
    column_name: str
    issues: list[BalanceSubmissionIssue]


def parse_submission_quantity(
    *,
    file_name: str,
    row_number: int,
    raw_quantity: str,
    issues: list[BalanceSubmissionIssue],
) -> Decimal | None:
    if not raw_quantity:
        return None
    try:
        quantity = parse_decimal(raw_quantity)
    except (ArithmeticError, InvalidOperation, ValueError) as exc:
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name="quantity",
                issue_kind="invalid_decimal",
                message=f"Could not parse quantity as Decimal: {exc}",
            )
        )
        return None
    if quantity is not None:
        return quantity
    issues.append(
        BalanceSubmissionIssue(
            file_name=file_name,
            row_number=str(row_number),
            column_name="quantity",
            issue_kind="invalid_decimal",
            message="Could not parse quantity as Decimal.",
        )
    )
    return None


def parse_submission_precision(
    *,
    file_name: str,
    row_number: int,
    column_name: str,
    raw_precision: str,
    issues: list[BalanceSubmissionIssue],
) -> TemporalPrecision | None:
    if not raw_precision:
        return None
    precision = parse_temporal_precision(raw_precision)
    if precision is not None:
        return precision
    issues.append(
        BalanceSubmissionIssue(
            file_name=file_name,
            row_number=str(row_number),
            column_name=column_name,
            issue_kind="invalid_precision",
            message=f"Unsupported {column_name} {raw_precision!r}.",
        )
    )
    return None


def parse_submission_temporal_value(
    *,
    context: SubmissionFieldContext,
    raw_value: str,
    precision: TemporalPrecision | None,
) -> datetime | None:
    if not raw_value or precision is None:
        return None
    try:
        return parse_temporal_value(raw_value, precision=precision)
    except ValueError as exc:
        context.issues.append(
            BalanceSubmissionIssue(
                file_name=context.file_name,
                row_number=str(context.row_number),
                column_name=context.column_name,
                issue_kind="invalid_timestamp",
                message=str(exc),
            )
        )
        return None


def parse_submission_reviewed_at(
    *,
    file_name: str,
    row_number: int,
    raw_reviewed_at: str,
    issues: list[BalanceSubmissionIssue],
) -> datetime | None:
    if not raw_reviewed_at:
        return None
    try:
        return parse_timestamp(raw_reviewed_at)
    except ValueError as exc:
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name="reviewed_at",
                issue_kind="invalid_timestamp",
                message=str(exc),
            )
        )
        return None
