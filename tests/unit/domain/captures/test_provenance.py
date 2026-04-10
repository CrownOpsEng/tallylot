from __future__ import annotations

import pytest

from tallylot.domain.captures import (
    ProvenanceLocator,
    empty_provenance_locator_dict,
    flatten_optional_provenance,
    provenance_locator_header,
)
from tallylot.domain.types import CaptureUid


def test_provenance_locator_round_trips_through_flat_dict() -> None:
    locator = ProvenanceLocator(
        capture_uid=CaptureUid("01HV4A5H7VJH7M3Y5A6B7C8D9E"),
        relative_path="statements/march.pdf",
        archive_member_path="inner/march.pdf",
        locator_kind="statement_pdf",
        anchor="page=2",
    )

    assert ProvenanceLocator.from_flat_dict(locator.to_flat_dict()) == locator
    assert ProvenanceLocator.from_reference_ref(
        locator.to_reference_ref()
    ) == ProvenanceLocator(
        capture_uid=CaptureUid(""),
        relative_path="statements/march.pdf",
        archive_member_path="inner/march.pdf",
        locator_kind="raw_file",
        anchor="page=2",
    )
    assert provenance_locator_header("raw") == (
        "raw_capture_uid",
        "raw_relative_path",
        "raw_archive_member_path",
        "raw_locator_kind",
        "raw_anchor",
    )
    assert empty_provenance_locator_dict(prefix="raw") == {
        "raw_capture_uid": "",
        "raw_relative_path": "",
        "raw_archive_member_path": "",
        "raw_locator_kind": "",
        "raw_anchor": "",
    }
    assert flatten_optional_provenance(None, prefix="raw") == {
        "raw_capture_uid": "",
        "raw_relative_path": "",
        "raw_archive_member_path": "",
        "raw_locator_kind": "",
        "raw_anchor": "",
    }


def test_provenance_locator_requires_relative_path() -> None:
    with pytest.raises(ValueError, match="relative_path must not be blank"):
        ProvenanceLocator(
            capture_uid=CaptureUid("01HV4A5H7VJH7M3Y5A6B7C8D9E"),
            relative_path="",
        )
