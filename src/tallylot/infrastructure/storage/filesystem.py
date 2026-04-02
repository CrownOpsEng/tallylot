"""Filesystem-backed fact and evidence repositories."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TypeVar

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import (
    EconomicLeg,
    FactClassification,
    FactDirection,
    FactLegPolicy,
    TransactionFact,
    parse_economic_kind,
    parse_journal_intent,
    parse_projection_type,
    parse_tax_treatment_code,
)
from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from tallylot.domain.value_objects import parse_decimal, parse_timestamp
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.evidence import WalletInventoryRecord

EnumT = TypeVar("EnumT")

WALLET_INVENTORY_HEADER = (
    "source",
    "capture_path",
    "wallet_id",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scope",
    "controller",
    "account_label",
    "evidence_kind",
    "evidence_path",
    "confidence",
    "account",
    "wallet",
    "identifier_value",
    "notes",
)


class FilesystemFactRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def read_facts(self, path: Path) -> tuple[TransactionFact, ...]:
        rows = self._artifacts.read_rows(path)
        return tuple(_fact_from_row(row) for row in rows)

    def write_facts(self, path: Path, facts: tuple[TransactionFact, ...]) -> None:
        write_rows(
            path,
            (
                "fact_id",
                "source",
                "adapter_id",
                "timestamp",
                "account",
                "wallet",
                "max_in_legs",
                "max_out_legs",
                "max_fee_legs",
                "economic_kind",
                "projection_type",
                "journal_intent",
                "tax_treatment_code",
                "description",
                "provider_operation_key",
                "operation_group_id",
                "tx_hash",
                "raw_file",
                "raw_row_ref",
                "confidence",
                "status",
                "legs",
                "fee_legs",
            ),
            (fact.to_row() for fact in facts),
        )


class FilesystemEvidenceRepository:
    def write_balance_snapshots(self, path: Path, balances: tuple[BalanceSnapshot, ...]) -> None:
        write_rows(
            path,
            ("source", "account", "wallet", "asset", "quantity", "as_of", "balance_kind", "notes"),
            (balance.to_row() for balance in balances),
        )

    def write_balance_evidence(self, path: Path, evidence: tuple[BalanceEvidence, ...]) -> None:
        write_rows(
            path,
            ("source", "account", "wallet", "asset", "quantity", "as_of", "balance_kind", "evidence_ref", "notes"),
            (record.to_row() for record in evidence),
        )

    def write_issue_records(self, path: Path, issues: tuple[IssueRecord, ...]) -> None:
        write_rows(
            path,
            (
                "issue_id",
                "source",
                "adapter_id",
                "severity",
                "kind",
                "message",
                "context_timestamp",
                "raw_file",
                "raw_row_ref",
                "status",
            ),
            (issue.to_row() for issue in issues),
        )

    def write_review_records(
        self,
        path: Path,
        reviews: tuple[NormalizationReviewRecord, ...],
    ) -> None:
        write_rows(
            path,
            (
                "review_id",
                "source",
                "adapter_id",
                "scope",
                "kind",
                "message",
                "raw_file",
                "raw_row_ref",
                "field_name",
                "original_value",
                "normalized_value",
                "status",
            ),
            (review.to_row() for review in reviews),
        )

    def write_wallet_inventory(self, path: Path, wallet_inventory: tuple[WalletInventoryRecord, ...]) -> None:
        write_rows(path, WALLET_INVENTORY_HEADER, (record.to_row() for record in wallet_inventory))


def _fact_from_row(row: dict[str, str]) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId(row["fact_id"]),
        source=SourceId(row["source"]),
        adapter_id=AdapterId(row["adapter_id"]),
        timestamp=parse_timestamp(row["timestamp"]),
        account=row["account"],
        wallet=row["wallet"],
        leg_policy=FactLegPolicy(
            max_in_legs=_required_int(row.get("max_in_legs"), "max_in_legs"),
            max_out_legs=_required_int(row.get("max_out_legs"), "max_out_legs"),
            max_fee_legs=_required_int(row.get("max_fee_legs"), "max_fee_legs"),
        ),
        classification=FactClassification(
            economic_kind=_required_enum(parse_economic_kind(row["economic_kind"]), "economic_kind"),
            journal_intent=_required_enum(parse_journal_intent(row["journal_intent"]), "journal_intent"),
            tax_treatment_code=_required_enum(
                parse_tax_treatment_code(row["tax_treatment_code"]),
                "tax_treatment_code",
            ),
            projection_type=parse_projection_type(row.get("projection_type", "")),
        ),
        legs=_legs_from_text(row.get("legs", "")),
        fee_legs=_legs_from_text(row.get("fee_legs", "")),
        description=row.get("description", ""),
        provider_operation_key=row.get("provider_operation_key", ""),
        operation_group_id=row.get("operation_group_id", ""),
        tx_hash=row.get("tx_hash") or None,
        raw_file=row.get("raw_file", ""),
        raw_row_ref=row.get("raw_row_ref", ""),
        confidence=row.get("confidence", "high"),
        status=row.get("status", "mapped"),
    )


def _legs_from_text(value: str) -> tuple[EconomicLeg, ...]:
    if not value:
        return ()
    legs: list[EconomicLeg] = []
    for raw_leg in value.split("|"):
        direction, asset, amount, account, wallet = raw_leg.split(":", maxsplit=4)
        legs.append(
            EconomicLeg(
                direction=_parse_fact_direction(direction),
                asset=AssetSymbol(asset),
                amount=_required_decimal(parse_decimal(amount), "leg.amount"),
                account=account,
                wallet=wallet,
            )
        )
    return tuple(legs)


def _parse_fact_direction(value: str) -> FactDirection:
    if value == "in":
        return "in"
    if value == "out":
        return "out"
    raise ValueError(f"unsupported fact leg direction: {value}")


def _required_enum(enum_value: EnumT | None, label: str) -> EnumT:
    if enum_value is None:
        raise ValueError(f"missing required enum field: {label}")
    return enum_value


def _required_decimal(value: Decimal | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"missing required decimal field: {label}")
    return value


def _required_int(value: str | None, label: str) -> int:
    if value is None or not value.strip():
        raise ValueError(f"missing required integer field: {label}")
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"invalid integer field {label}: {value}") from error
