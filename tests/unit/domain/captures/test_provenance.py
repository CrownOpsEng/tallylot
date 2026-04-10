from __future__ import annotations

import pytest

from tallylot.domain.captures import ProvenanceLocator
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


def test_provenance_locator_requires_relative_path() -> None:
    with pytest.raises(ValueError, match="relative_path must not be blank"):
        ProvenanceLocator(
            capture_uid=CaptureUid("01HV4A5H7VJH7M3Y5A6B7C8D9E"),
            relative_path="",
        )
