"""Structured CSV row validation and amount normalization."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.value_objects import format_decimal, parse_decimal, parse_timestamp

from .contracts import ReviewSpec, ReviewValues
from .feedback import StructuredCsvFeedbackFactory


@dataclass(frozen=True)
class StructuredCsvRowValidator:
    feedback: StructuredCsvFeedbackFactory

    def validate_row(
        self,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        validators = (
            self._validate_required_text_fields,
            self._validate_amount_pairs,
            self._validate_event_amount_presence,
            self._validate_timestamp_field,
            self._validate_numeric_fields,
            self._validate_side_fields,
        )
        for validator in validators:
            issue = validator(row, index)
            if issue is not None:
                return issue
        return None

    def normalize_outbound_amount(
        self,
        index: int,
        field_name: str,
        raw_value: str | None,
    ) -> tuple[Decimal | None, NormalizationReviewRecord | None]:
        value = parse_decimal(raw_value)
        if value is None:
            return None, None
        if value < Decimal("0"):
            normalized_amount = value.copy_abs()
            return normalized_amount, self.feedback.review(
                index=index,
                spec=ReviewSpec(
                    kind="outbound_amount_sign_normalized",
                    message=f"{field_name} was negative and was normalized to a positive outbound value.",
                    values=ReviewValues(
                        field_name=field_name,
                        original_value=(raw_value or "").strip(),
                        normalized_value=format_decimal(normalized_amount),
                    ),
                ),
            )
        return value, None

    def _validate_required_text_fields(
        self,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        missing_text_fields = [
            field_name
            for field_name in ("timestamp", "category", "account", "wallet")
            if not (row.get(field_name) or "").strip()
        ]
        if not missing_text_fields:
            return None
        return self.feedback.issue(
            index,
            "missing_required_field",
            f"Missing required field(s): {', '.join(missing_text_fields)}.",
        )

    def _validate_amount_pairs(
        self,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        for asset_field, amount_field, side_field in (
            ("asset_in", "amount_in", None),
            ("asset_out", "amount_out", None),
            ("charge_asset", "charge_amount", "charge_side"),
            ("rebate_asset", "rebate_amount", "rebate_side"),
        ):
            asset_value = (row.get(asset_field) or "").strip()
            amount_value = (row.get(amount_field) or "").strip()
            if bool(asset_value) != bool(amount_value):
                return self.feedback.issue(
                    index,
                    "incomplete_amount_pair",
                    f"{asset_field} and {amount_field} must both be present or both be blank.",
                )
            if side_field is not None and (row.get(side_field) or "").strip() and not asset_value:
                return self.feedback.issue(
                    index,
                    "incomplete_amount_pair",
                    f"{side_field} requires {asset_field} and {amount_field}.",
                )
        return None

    def _validate_event_amount_presence(
        self,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        if (row["asset_in"] or "").strip() or (row["asset_out"] or "").strip():
            return None
        return self.feedback.issue(
            index,
            "missing_event_amount",
            "A row must include either an inbound or outbound asset amount.",
        )

    def _validate_timestamp_field(
        self,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        try:
            parse_timestamp((row["timestamp"] or "").strip())
        except ValueError:
            return self.feedback.issue(
                index,
                "invalid_timestamp",
                f"Unsupported timestamp value: {(row['timestamp'] or '').strip()!r}.",
            )
        return None

    def _validate_numeric_fields(
        self,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        for field_name in ("amount_in", "amount_out", "charge_amount", "rebate_amount"):
            try:
                parsed_value = parse_decimal((row.get(field_name) or "").strip())
            except (InvalidOperation, ValueError):
                return self.feedback.issue(
                    index,
                    "invalid_decimal",
                    f"Unsupported decimal value for {field_name}: {(row.get(field_name) or '').strip()!r}.",
                )
            if parsed_value == Decimal("0"):
                return self.feedback.issue(
                    index,
                    "zero_amount",
                    f"{field_name} must be greater than zero when present.",
                )
            if (
                field_name in {"amount_in", "rebate_amount"}
                and parsed_value is not None
                and parsed_value < Decimal("0")
            ):
                return self.feedback.issue(
                    index,
                    "conflicting_amount_sign",
                    f"{field_name} cannot be negative.",
                )
        return None

    def _validate_side_fields(
        self,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        for field_name in ("charge_side", "rebate_side"):
            side_value = (row.get(field_name) or "").strip()
            if side_value and side_value not in {"in", "out"}:
                return self.feedback.issue(
                    index,
                    "invalid_side_value",
                    f"{field_name} must be 'in', 'out', or blank.",
                )
        return None
