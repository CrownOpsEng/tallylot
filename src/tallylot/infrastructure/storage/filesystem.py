"""Filesystem-backed fact and evidence repositories."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import TypeVar, cast

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import (
    EconomicLeg,
    FactClassification,
    FactDirection,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
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
JsonDict = dict[str, object]

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
                "leg_policy",
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
                "context_timestamp",
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
        leg_policy=_policy_from_text(row.get("leg_policy", "")),
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
    raw_legs = _json_array(value, label="legs")
    legs: list[EconomicLeg] = []
    for raw_leg in raw_legs:
        legs.append(
            EconomicLeg(
                direction=_parse_fact_direction(_required_str(raw_leg, "direction")),
                kind=LegKind(_required_str(raw_leg, "kind")),
                asset=AssetSymbol(_required_str(raw_leg, "asset")),
                amount=_required_decimal(parse_decimal(_required_str(raw_leg, "amount")), "leg.amount"),
                subtype=_optional_str(raw_leg, "subtype"),
                attributed_to_direction=_optional_fact_direction(raw_leg, "attributed_to_direction"),
                account=_optional_str(raw_leg, "account") or "",
                wallet=_optional_str(raw_leg, "wallet") or "",
            )
        )
    return tuple(legs)


def _policy_from_text(value: str) -> FactLegPolicy:
    raw_limits = _json_array(value, label="leg_policy")
    return FactLegPolicy(
        limits=tuple(
            LegShapeLimit(
                kind=LegKind(_required_str(raw_limit, "kind")),
                max_count=_required_int_value(raw_limit, "max_count"),
                max_in_count=_optional_int_value(raw_limit, "max_in_count"),
                max_out_count=_optional_int_value(raw_limit, "max_out_count"),
            )
            for raw_limit in raw_limits
        )
    )


def _json_array(value: str, *, label: str) -> list[JsonDict]:
    try:
        payload: object = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON field {label}") from error
    if not isinstance(payload, list):
        raise ValueError(f"invalid JSON field {label}: expected array")
    normalized_payload: list[JsonDict] = []
    for item in cast(list[object], payload):
        if not isinstance(item, dict):
            raise ValueError(f"invalid JSON field {label}: expected array of objects")
        normalized_payload.append(cast(JsonDict, item))
    return normalized_payload


def _parse_fact_direction(value: str) -> FactDirection:
    if value == "in":
        return "in"
    if value == "out":
        return "out"
    raise ValueError(f"unsupported fact leg direction: {value}")


def _optional_fact_direction(raw: JsonDict, key: str) -> FactDirection | None:
    value = _optional_str(raw, key)
    if value is None:
        return None
    return _parse_fact_direction(value)


def _required_enum(enum_value: EnumT | None, label: str) -> EnumT:
    if enum_value is None:
        raise ValueError(f"missing required enum field: {label}")
    return enum_value


def _required_decimal(value: Decimal | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"missing required decimal field: {label}")
    return value


def _required_str(raw: JsonDict, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing required string field: {key}")
    return value


def _optional_str(raw: JsonDict, key: str) -> str | None:
    value = raw.get(key)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid string field: {key}")
    return value


def _required_int_value(raw: JsonDict, key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"missing required integer field: {key}")
    return value


def _optional_int_value(raw: JsonDict, key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"invalid integer field: {key}")
    return value
