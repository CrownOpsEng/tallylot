"""Structured CSV source adapter."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    CanonicalBalance,
    CanonicalEvent,
    FileInventoryEntry,
    IssueRecord,
    NormalizationReviewRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, SourceId
from crypto_reconciliation.domain.value_objects import format_decimal, parse_decimal, parse_timestamp
from crypto_reconciliation.ports.adapters import NormalizationResult

REQUIRED_HEADER = (
    "timestamp",
    "event_kind",
    "asset_in",
    "amount_in",
    "asset_out",
    "amount_out",
    "fee_asset",
    "fee_amount",
    "tx_hash",
    "description",
    "account",
    "wallet",
)


@dataclass(frozen=True)
class ReviewValues:
    field_name: str = ""
    original_value: str = ""
    normalized_value: str = ""


EMPTY_REVIEW_VALUES = ReviewValues()


@dataclass(frozen=True)
class ReviewSpec:
    kind: str
    message: str
    values: ReviewValues = EMPTY_REVIEW_VALUES


class StructuredCsvSourceAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("structured_csv"),
        display_name="Structured CSV",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.WALLET_INVENTORY}),
        description="Normalizes a strongly typed structured CSV source capture.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del source, raw_dir
        for item in inventory:
            if item.relative_path == "transactions.csv" and item.header == REQUIRED_HEADER:
                return 100
        return 0

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        path = raw_dir / "transactions.csv"
        events: list[CanonicalEvent] = []
        issues: list[IssueRecord] = []
        reviews: list[NormalizationReviewRecord] = []
        balances: dict[tuple[str, str, str], Decimal] = {}
        wallet_rows: dict[str, WalletInventoryRecord] = {}
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != REQUIRED_HEADER:
                return NormalizationResult(
                    canonical_events=(),
                    canonical_balances=(),
                    issues=(
                        IssueRecord(
                            issue_id=f"{profile.source}:schema",
                            source=str(profile.source),
                            adapter_id=str(self.manifest.adapter_id),
                            severity="high",
                            kind="invalid_schema",
                            message="transactions.csv does not match the structured CSV schema.",
                            raw_file="transactions.csv",
                        ),
                    ),
                    reviews=(),
                    wallet_inventory=(),
                )
            for index, row in enumerate(reader, start=2):
                row_issue = self._validate_row(profile, row, index)
                if row_issue is not None:
                    issues.append(row_issue)
                    continue

                timestamp = parse_timestamp(row["timestamp"])
                amount_in = parse_decimal(row["amount_in"])
                amount_out, amount_out_review = self._canonicalize_outbound_amount(
                    profile,
                    index,
                    "amount_out",
                    row["amount_out"],
                )
                fee_amount, fee_amount_review = self._canonicalize_outbound_amount(
                    profile,
                    index,
                    "fee_amount",
                    row["fee_amount"],
                )
                account = row["account"].strip()
                wallet = row["wallet"].strip()
                if amount_out_review is not None:
                    reviews.append(amount_out_review)
                if fee_amount_review is not None:
                    reviews.append(fee_amount_review)
                events.append(
                    CanonicalEvent(
                        event_id=EventId(f"{profile.source}:{index}"),
                        source=SourceId(str(profile.source)),
                        adapter_id=AdapterId(str(self.manifest.adapter_id)),
                        account=account,
                        wallet=wallet,
                        timestamp=timestamp,
                        event_kind=row["event_kind"],
                        description=row["description"],
                        asset_in=AssetSymbol(row["asset_in"]) if row["asset_in"] else None,
                        amount_in=amount_in,
                        asset_out=AssetSymbol(row["asset_out"]) if row["asset_out"] else None,
                        amount_out=amount_out,
                        fee_asset=AssetSymbol(row["fee_asset"]) if row["fee_asset"] else None,
                        fee_amount=fee_amount,
                        tx_hash=row["tx_hash"] or None,
                        raw_file="transactions.csv",
                        raw_row_ref=str(index),
                        render_type=row["event_kind"],
                        render_exchange=account,
                        render_comment=row["description"],
                    )
                )
                if row["asset_in"] and amount_in is not None:
                    key = (account, wallet, row["asset_in"])
                    balances[key] = balances.get(key, Decimal("0")) + amount_in
                if row["asset_out"] and amount_out is not None:
                    key = (account, wallet, row["asset_out"])
                    balances[key] = balances.get(key, Decimal("0")) - amount_out
                if row["fee_asset"] and fee_amount is not None:
                    key = (account, wallet, row["fee_asset"])
                    balances[key] = balances.get(key, Decimal("0")) - fee_amount
                wallet_id = f"{profile.source}:{account}:{wallet}"
                wallet_rows[wallet_id] = WalletInventoryRecord(
                    wallet_id=wallet_id,
                    source=str(profile.source),
                    account=account,
                    wallet=wallet,
                    evidence_path="transactions.csv",
                    identifier_kind="account_wallet",
                    identifier_value=f"{account}:{wallet}",
                )

        if events:
            reviews.extend(
                (
                    self._dataset_review(
                        profile,
                        "timestamp_timezone_assumed_utc",
                        (
                            "Structured CSV timestamps are timezone-naive; normalization assigns UTC "
                            "and those timestamps should be validated against the source system."
                        ),
                    ),
                    self._dataset_review(
                        profile,
                        "default_render_mapping",
                        (
                            "Structured CSV normalization defaults CoinTracking render fields to "
                            "render_type<-event_kind, render_exchange<-account, and "
                            "render_comment<-description; validate those mappings before import."
                        ),
                    ),
                )
            )

        as_of = max(event.timestamp for event in events) if events else datetime.now(UTC)
        balance_rows = tuple(
            CanonicalBalance(
                source=SourceId(str(profile.source)),
                account=account,
                wallet=wallet,
                asset=AssetSymbol(asset),
                quantity=quantity,
                as_of=as_of,
            )
            for (account, wallet, asset), quantity in sorted(balances.items())
        )
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=balance_rows,
            issues=tuple(
                issues
                if events
                else [
                    *issues,
                    IssueRecord(
                        issue_id=f"{profile.source}:no_valid_rows",
                        source=str(profile.source),
                        adapter_id=str(self.manifest.adapter_id),
                        severity="high",
                        kind="no_valid_rows",
                        message="No valid rows were available for normalization.",
                        raw_file="transactions.csv",
                    ),
                ]
            ),
            reviews=tuple(reviews),
            wallet_inventory=tuple(wallet_rows.values()),
        )

    def _validate_row(
        self,
        profile: SourceProfile,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        validators = (
            self._validate_required_text_fields,
            self._validate_amount_pairs,
            self._validate_event_amount_presence,
            self._validate_timestamp_field,
            self._validate_numeric_fields,
        )
        for validator in validators:
            issue = validator(profile, row, index)
            if issue is not None:
                return issue
        return None

    def _validate_required_text_fields(
        self,
        profile: SourceProfile,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        missing_text_fields = [
            field_name
            for field_name in ("timestamp", "event_kind", "account", "wallet")
            if not (row.get(field_name) or "").strip()
        ]
        if missing_text_fields:
            return self._issue(
                profile,
                index,
                "missing_required_field",
                f"Missing required field(s): {', '.join(missing_text_fields)}.",
            )
        return None

    def _validate_amount_pairs(
        self,
        profile: SourceProfile,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        for asset_field, amount_field in (
            ("asset_in", "amount_in"),
            ("asset_out", "amount_out"),
            ("fee_asset", "fee_amount"),
        ):
            asset_value = (row.get(asset_field) or "").strip()
            amount_value = (row.get(amount_field) or "").strip()
            if bool(asset_value) != bool(amount_value):
                return self._issue(
                    profile,
                    index,
                    "incomplete_amount_pair",
                    f"{asset_field} and {amount_field} must both be present or both be blank.",
                )
        return None

    def _validate_event_amount_presence(
        self,
        profile: SourceProfile,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        if not (row["asset_in"] or "").strip() and not (row["asset_out"] or "").strip():
            return self._issue(
                profile,
                index,
                "missing_event_amount",
                "A row must include either an inbound or outbound asset amount.",
            )
        return None

    def _validate_timestamp_field(
        self,
        profile: SourceProfile,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        try:
            parse_timestamp((row["timestamp"] or "").strip())
        except ValueError:
            return self._issue(
                profile,
                index,
                "invalid_timestamp",
                f"Unsupported timestamp value: {(row['timestamp'] or '').strip()!r}.",
            )
        return None

    def _validate_numeric_fields(
        self,
        profile: SourceProfile,
        row: dict[str, str | None],
        index: int,
    ) -> IssueRecord | None:
        for field_name in ("amount_in", "amount_out", "fee_amount"):
            try:
                parsed_value = parse_decimal((row.get(field_name) or "").strip())
            except (InvalidOperation, ValueError):
                return self._issue(
                    profile,
                    index,
                    "invalid_decimal",
                    f"Unsupported decimal value for {field_name}: {(row.get(field_name) or '').strip()!r}.",
                )
            if parsed_value == Decimal("0"):
                return self._issue(
                    profile,
                    index,
                    "zero_amount",
                    f"{field_name} must be greater than zero when present.",
                )
            if field_name == "amount_in" and parsed_value is not None and parsed_value < Decimal("0"):
                return self._issue(
                    profile,
                    index,
                    "conflicting_amount_sign",
                    "amount_in cannot be negative; use amount_out for outbound value flows.",
                )

        return None

    def _canonicalize_outbound_amount(
        self,
        profile: SourceProfile,
        index: int,
        field_name: str,
        raw_value: str | None,
    ) -> tuple[Decimal | None, NormalizationReviewRecord | None]:
        value = parse_decimal(raw_value)
        if value is None:
            return None, None
        if value < Decimal("0"):
            canonical = value.copy_abs()
            return canonical, self._review(
                profile,
                index=index,
                spec=ReviewSpec(
                    kind="outbound_amount_sign_canonicalized",
                    message=f"{field_name} was negative and was canonicalized to a positive outbound value.",
                    values=ReviewValues(
                        field_name=field_name,
                        original_value=(raw_value or "").strip(),
                        normalized_value=format_decimal(canonical),
                    ),
                ),
            )
        return value, None

    def _issue(
        self,
        profile: SourceProfile,
        index: int,
        kind: str,
        message: str,
    ) -> IssueRecord:
        return IssueRecord(
            issue_id=f"{profile.source}:{index}:{kind}",
            source=str(profile.source),
            adapter_id=str(self.manifest.adapter_id),
            severity="high",
            kind=kind,
            message=message,
            raw_file="transactions.csv",
            raw_row_ref=str(index),
        )

    def _dataset_review(
        self,
        profile: SourceProfile,
        kind: str,
        message: str,
    ) -> NormalizationReviewRecord:
        return self._review(profile, index=None, spec=ReviewSpec(kind=kind, message=message))

    def _review(
        self,
        profile: SourceProfile,
        *,
        index: int | None,
        spec: ReviewSpec,
    ) -> NormalizationReviewRecord:
        review_id = (
            f"{profile.source}:{index}:{spec.kind}" if index is not None else f"{profile.source}:dataset:{spec.kind}"
        )
        return NormalizationReviewRecord(
            review_id=review_id,
            source=str(profile.source),
            adapter_id=str(self.manifest.adapter_id),
            scope="row" if index is not None else "dataset",
            kind=spec.kind,
            message=spec.message,
            raw_file="transactions.csv",
            raw_row_ref="" if index is None else str(index),
            field_name=spec.values.field_name,
            original_value=spec.values.original_value,
            normalized_value=spec.values.normalized_value,
        )


ADAPTER = StructuredCsvSourceAdapter()
