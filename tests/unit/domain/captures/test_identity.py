from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from tallylot.domain.captures import (
    CaptureIdentity,
    format_capture_label,
    generate_capture_uid,
    is_capture_uid,
)


def test_generate_capture_uid_returns_ulid() -> None:
    capture_uid = generate_capture_uid(
        now=datetime(2026, 3, 23, 14, 15, 16, tzinfo=UTC),
        randomness=b"\x00" * 10,
    )

    assert is_capture_uid(str(capture_uid))
    assert len(str(capture_uid)) == 26


def test_capture_uid_sorts_by_timestamp() -> None:
    earlier = generate_capture_uid(
        now=datetime(2026, 3, 23, 14, 15, 16, tzinfo=UTC),
        randomness=b"\x00" * 10,
    )
    later = generate_capture_uid(
        now=datetime(2026, 3, 23, 14, 15, 17, tzinfo=UTC),
        randomness=b"\x00" * 10,
    )

    assert str(earlier) < str(later)


def test_format_capture_label_uses_utc_second_precision() -> None:
    assert (
        format_capture_label(datetime(2026, 3, 23, 14, 15, 16, tzinfo=UTC))
        == "2026-03-23T14-15-16Z"
    )


def test_capture_identity_is_frozen() -> None:
    identity = CaptureIdentity(
        capture_uid=generate_capture_uid(
            now=datetime(2026, 3, 23, 14, 15, 16, tzinfo=UTC),
            randomness=b"\x01" * 10,
        ),
        capture_label="2026-03-23T14-15-16Z",
    )

    with pytest.raises(FrozenInstanceError):
        setattr(identity, "capture_label", "changed")
