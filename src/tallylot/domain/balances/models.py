"""Shared balance models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    format_timestamp,
    require_temporal_datetime,
    require_utc_datetime,
)

from .kinds import normalize_balance_kind


class BalanceReferenceKind(StrEnum):
    SOURCE_DOCUMENT = "source_document"
    NETWORK_API = "network_api"
    OPERATOR_ASSERTION = "operator_assertion"


class BalanceAssertionStatus(StrEnum):
    MATCHED = "matched"
    DRIFT = "drift"
    MISSING_SNAPSHOT = "missing_snapshot"
    MISSING_REFERENCE = "missing_reference"
    REFERENCE_CONFLICT = "reference_conflict"


@dataclass(frozen=True, order=True)
class BalanceTarget:
    source: SourceId
    location_id: LocationId
    instrument_id: InstrumentId
    balance_kind: str
    target_at: datetime
    target_precision: TemporalPrecision

    def __post_init__(self) -> None:
        if not str(self.instrument_id):
            raise ValueError("balance target instrument_id must not be blank")
        object.__setattr__(
            self, "balance_kind", normalize_balance_kind(self.balance_kind)
        )
        object.__setattr__(
            self,
            "target_at",
            require_temporal_datetime(
                self.target_at,
                precision=self.target_precision,
                label="balance target target_at",
            ),
        )

    def to_row(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "location_id": str(self.location_id),
            "instrument_id": str(self.instrument_id),
            "balance_kind": self.balance_kind,
            "target_at": format_temporal_value(
                self.target_at,
                precision=self.target_precision,
                label="balance target target_at",
            ),
            "target_precision": self.target_precision.value,
        }


@dataclass(frozen=True)
class BalanceSnapshot:
    target: BalanceTarget
    quantity: Decimal
    snapshot_basis: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.snapshot_basis.strip():
            raise ValueError("balance snapshot snapshot_basis must not be blank")

    @property
    def source(self) -> SourceId:
        return self.target.source

    @property
    def location_id(self) -> LocationId:
        return self.target.location_id

    @property
    def instrument_id(self) -> InstrumentId:
        return self.target.instrument_id

    @property
    def balance_kind(self) -> str:
        return self.target.balance_kind

    @property
    def target_at(self) -> datetime:
        return self.target.target_at

    @property
    def target_precision(self) -> TemporalPrecision:
        return self.target.target_precision

    def to_row(self) -> dict[str, str]:
        return {
            **self.target.to_row(),
            "quantity": format_decimal(self.quantity),
            "snapshot_basis": self.snapshot_basis,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class BalanceReference:
    target: BalanceTarget
    quantity: Decimal
    reference_kind: BalanceReferenceKind
    observed_at: datetime
    observed_precision: TemporalPrecision
    support_ref: str = ""
    provider_family: str = ""
    provider_locator: str = ""
    provider_block_ref: str = ""
    reviewed_by: str = ""
    reviewed_at: datetime | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observed_at",
            require_temporal_datetime(
                self.observed_at,
                precision=self.observed_precision,
                label="balance reference observed_at",
            ),
        )
        reviewed_by = self.reviewed_by.strip()
        reviewed_at = self.reviewed_at
        provider_family = self.provider_family.strip()
        provider_locator = self.provider_locator.strip()
        provider_block_ref = self.provider_block_ref.strip()
        support_ref = self.support_ref.strip()
        if self.reference_kind is BalanceReferenceKind.OPERATOR_ASSERTION:
            if not reviewed_by:
                raise ValueError(
                    "operator assertion balance references require reviewed_by"
                )
            if reviewed_at is None:
                raise ValueError(
                    "operator assertion balance references require reviewed_at"
                )
        elif reviewed_at is not None and not reviewed_by:
            raise ValueError("balance reference reviewed_at requires reviewed_by")
        if (
            self.reference_kind is BalanceReferenceKind.NETWORK_API
            and not provider_family
        ):
            raise ValueError("network api balance references require provider_family")
        if self.reference_kind is not BalanceReferenceKind.NETWORK_API and (
            provider_family or provider_locator or provider_block_ref
        ):
            raise ValueError(
                "only network api balance references may set provider fields"
            )
        if reviewed_at is not None:
            object.__setattr__(
                self,
                "reviewed_at",
                require_utc_datetime(
                    reviewed_at,
                    label="balance reference reviewed_at",
                ),
            )
        object.__setattr__(self, "reviewed_by", reviewed_by)
        object.__setattr__(self, "provider_family", provider_family)
        object.__setattr__(self, "provider_locator", provider_locator)
        object.__setattr__(self, "provider_block_ref", provider_block_ref)
        object.__setattr__(self, "support_ref", support_ref)

    @property
    def source(self) -> SourceId:
        return self.target.source

    @property
    def location_id(self) -> LocationId:
        return self.target.location_id

    @property
    def instrument_id(self) -> InstrumentId:
        return self.target.instrument_id

    @property
    def balance_kind(self) -> str:
        return self.target.balance_kind

    @property
    def target_at(self) -> datetime:
        return self.target.target_at

    @property
    def target_precision(self) -> TemporalPrecision:
        return self.target.target_precision

    def to_row(self) -> dict[str, str]:
        reviewed_at = self.reviewed_at
        return {
            **self.target.to_row(),
            "quantity": format_decimal(self.quantity),
            "reference_kind": self.reference_kind.value,
            "observed_at": format_temporal_value(
                self.observed_at,
                precision=self.observed_precision,
                label="balance reference observed_at",
            ),
            "observed_precision": self.observed_precision.value,
            "support_ref": self.support_ref,
            "provider_family": self.provider_family,
            "provider_locator": self.provider_locator,
            "provider_block_ref": self.provider_block_ref,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": "" if reviewed_at is None else format_timestamp(reviewed_at),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class BalanceAssertion:
    target: BalanceTarget
    snapshot_quantity: Decimal | None
    reference_quantity: Decimal | None
    difference: Decimal
    status: BalanceAssertionStatus
    selected_reference_kind: BalanceReferenceKind | None = None
    snapshot_basis: str = ""
    observed_at: datetime | None = None
    observed_precision: TemporalPrecision | None = None
    observation_gap: str = ""
    support_ref: str = ""
    provider_family: str = ""
    provider_block_ref: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.observed_at is None:
            if self.observed_precision is not None:
                raise ValueError(
                    "balance assertion observed_precision requires observed_at"
                )
        elif self.observed_precision is None:
            raise ValueError(
                "balance assertion observed_at requires observed_precision"
            )
        else:
            object.__setattr__(
                self,
                "observed_at",
                require_temporal_datetime(
                    self.observed_at,
                    precision=self.observed_precision,
                    label="balance assertion observed_at",
                ),
            )

    @property
    def source(self) -> SourceId:
        return self.target.source

    @property
    def location_id(self) -> LocationId:
        return self.target.location_id

    @property
    def instrument_id(self) -> InstrumentId:
        return self.target.instrument_id

    @property
    def balance_kind(self) -> str:
        return self.target.balance_kind

    @property
    def target_at(self) -> datetime:
        return self.target.target_at

    @property
    def target_precision(self) -> TemporalPrecision:
        return self.target.target_precision

    def to_row(self) -> dict[str, str]:
        return {
            **self.target.to_row(),
            "snapshot_quantity": format_decimal(self.snapshot_quantity),
            "reference_quantity": format_decimal(self.reference_quantity),
            "difference": format_decimal(self.difference),
            "status": self.status.value,
            "selected_reference_kind": (
                ""
                if self.selected_reference_kind is None
                else self.selected_reference_kind.value
            ),
            "snapshot_basis": self.snapshot_basis,
            "observed_at": (
                ""
                if self.observed_at is None or self.observed_precision is None
                else format_temporal_value(
                    self.observed_at,
                    precision=self.observed_precision,
                    label="balance assertion observed_at",
                )
            ),
            "observed_precision": (
                "" if self.observed_precision is None else self.observed_precision.value
            ),
            "observation_gap": self.observation_gap,
            "support_ref": self.support_ref,
            "provider_family": self.provider_family,
            "provider_block_ref": self.provider_block_ref,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class BalanceProviderRequest:
    target: BalanceTarget


@dataclass(frozen=True)
class BalanceProviderResult:
    target: BalanceTarget
    reference: BalanceReference | None = None
    issue_kind: str = ""
    issue_message: str = ""

    @property
    def supported(self) -> bool:
        return self.reference is not None and not self.issue_kind
