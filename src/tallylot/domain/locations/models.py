"""Neutral location records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from tallylot.domain.location_identifiers import require_location_id
from tallylot.domain.types import LocationId


class LocationKind(StrEnum):
    ACCOUNT = "account"
    ADDRESS = "address"
    CONTAINER = "container"
    POSITION = "position"
    SUBACCOUNT = "subaccount"
    SUBUNIT = "subunit"
    OTHER = "other"


@dataclass(frozen=True)
class LocationRecord:
    location_id: LocationId
    location_kind: LocationKind
    label: str
    parent_location_id: LocationId | None = None
    path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("location label must not be blank")
        if any(not segment.strip() for segment in self.path):
            raise ValueError("location path segments must not be blank")
        object.__setattr__(
            self,
            "location_id",
            require_location_id(str(self.location_id), label="location location_id"),
        )
        if self.parent_location_id is not None:
            object.__setattr__(
                self,
                "parent_location_id",
                require_location_id(
                    str(self.parent_location_id), label="location parent_location_id"
                ),
            )

    def to_row(self) -> dict[str, str]:
        return {
            "location_id": str(self.location_id),
            "location_kind": self.location_kind.value,
            "label": self.label,
            "parent_location_id": ""
            if self.parent_location_id is None
            else str(self.parent_location_id),
            "path": json.dumps(
                list(self.path), ensure_ascii=True, separators=(",", ":")
            ),
        }
