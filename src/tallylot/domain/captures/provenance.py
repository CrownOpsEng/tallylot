"""Capture-scoped provenance locators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from tallylot.domain.types import CaptureUid

PROVENANCE_LOCATOR_FIELDS = (
    "capture_uid",
    "relative_path",
    "archive_member_path",
    "locator_kind",
    "anchor",
)

PROVENANCE_LOCATOR_HEADER = PROVENANCE_LOCATOR_FIELDS


def provenance_locator_header(prefix: str = "") -> tuple[str, ...]:
    if not prefix:
        return PROVENANCE_LOCATOR_HEADER
    return tuple(f"{prefix}_{field}" for field in PROVENANCE_LOCATOR_FIELDS)


def _field_name(field: str, *, prefix: str = "") -> str:
    return f"{prefix}_{field}" if prefix else field


def empty_provenance_locator_dict(*, prefix: str = "") -> dict[str, str]:
    return {field_name: "" for field_name in provenance_locator_header(prefix)}


def flatten_optional_provenance(
    locator: ProvenanceLocator | None,
    *,
    prefix: str = "",
) -> dict[str, str]:
    if locator is None:
        return empty_provenance_locator_dict(prefix=prefix)
    return locator.to_flat_dict(prefix=prefix)


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

    def to_reference_ref(self) -> str:
        reference = self.relative_path
        if self.archive_member_path:
            reference = f"{reference}::{self.archive_member_path}"
        if self.anchor:
            reference = f"{reference}#{self.anchor}"
        return reference

    def to_flat_dict(self, *, prefix: str = "") -> dict[str, str]:
        return {
            _field_name("capture_uid", prefix=prefix): str(self.capture_uid),
            _field_name("relative_path", prefix=prefix): self.relative_path,
            _field_name("archive_member_path", prefix=prefix): self.archive_member_path,
            _field_name("locator_kind", prefix=prefix): self.locator_kind,
            _field_name("anchor", prefix=prefix): self.anchor,
        }

    @classmethod
    def from_reference_ref(
        cls,
        reference: str,
        *,
        capture_uid: CaptureUid | str = "",
        locator_kind: str = "raw_file",
    ) -> ProvenanceLocator:
        text = reference.strip()
        if not text:
            raise ValueError("reference must not be blank")
        path_part, anchor_separator, anchor = text.partition("#")
        relative_path, archive_member_path = path_part, ""
        if "::" in path_part:
            relative_path, archive_member_path = path_part.split("::", 1)
        return cls(
            capture_uid=CaptureUid(str(capture_uid)),
            relative_path=relative_path,
            archive_member_path=archive_member_path,
            locator_kind=locator_kind,
            anchor=anchor if anchor_separator else "",
        )

    @classmethod
    def from_flat_dict(
        cls,
        row: Mapping[str, str],
        *,
        prefix: str = "",
    ) -> ProvenanceLocator:
        return cls(
            capture_uid=CaptureUid(row[_field_name("capture_uid", prefix=prefix)]),
            relative_path=row[_field_name("relative_path", prefix=prefix)],
            archive_member_path=row.get(
                _field_name("archive_member_path", prefix=prefix),
                "",
            ),
            locator_kind=row.get(
                _field_name("locator_kind", prefix=prefix), "raw_file"
            ),
            anchor=row.get(_field_name("anchor", prefix=prefix), ""),
        )


def provenance_locator_from_row(
    row: Mapping[str, str],
    *,
    prefix: str = "",
) -> ProvenanceLocator | None:
    capture_uid_key = _field_name("capture_uid", prefix=prefix)
    relative_path_key = _field_name("relative_path", prefix=prefix)
    if (
        not row.get(capture_uid_key, "").strip()
        and not row.get(relative_path_key, "").strip()
    ):
        return None
    return ProvenanceLocator.from_flat_dict(row, prefix=prefix)
