"""Capture-scoped provenance locators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from tallylot.domain.types import CaptureUid

PROVENANCE_LOCATOR_HEADER = (
    "capture_uid",
    "relative_path",
    "archive_member_path",
    "locator_kind",
    "anchor",
)


@dataclass(frozen=True)
class ProvenanceLocator:
    capture_uid: CaptureUid
    relative_path: str
    archive_member_path: str = ""
    locator_kind: str = "raw_file"
    anchor: str = ""

    def __post_init__(self) -> None:
        if not self.relative_path.strip():
            raise ValueError("relative_path must not be blank")
        if not self.locator_kind.strip():
            raise ValueError("locator_kind must not be blank")

    def to_flat_dict(self) -> dict[str, str]:
        return {
            "capture_uid": str(self.capture_uid),
            "relative_path": self.relative_path,
            "archive_member_path": self.archive_member_path,
            "locator_kind": self.locator_kind,
            "anchor": self.anchor,
        }

    @classmethod
    def from_flat_dict(cls, row: Mapping[str, str]) -> ProvenanceLocator:
        return cls(
            capture_uid=CaptureUid(row["capture_uid"]),
            relative_path=row["relative_path"],
            archive_member_path=row.get("archive_member_path", ""),
            locator_kind=row.get("locator_kind", "raw_file"),
            anchor=row.get("anchor", ""),
        )
