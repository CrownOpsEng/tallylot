"""Capture identity helpers."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from tallylot.domain.types import CaptureUid
from tallylot.domain.value_objects import require_utc_datetime

_CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ULID_LENGTH = 26
_RANDOMNESS_BYTES = 10
_TIMESTAMP_BITS = 48
_RANDOMNESS_BITS = 80
_ULID_PATTERN = frozenset(_CROCKFORD_BASE32)


def generate_capture_uid(
    *,
    now: datetime | None = None,
    randomness: bytes | None = None,
) -> CaptureUid:
    capture_time = require_utc_datetime(
        now or datetime.now(UTC), label="capture_uid time"
    )
    timestamp_ms = int(capture_time.timestamp() * 1000)
    if timestamp_ms >= 1 << _TIMESTAMP_BITS:
        raise ValueError("capture_uid timestamp exceeds ULID range")
    entropy = randomness or secrets.token_bytes(_RANDOMNESS_BYTES)
    if len(entropy) != _RANDOMNESS_BYTES:
        raise ValueError("capture_uid randomness must be exactly 10 bytes")
    value = (timestamp_ms << _RANDOMNESS_BITS) | int.from_bytes(
        entropy, byteorder="big"
    )
    encoded = "".join(
        _CROCKFORD_BASE32[(value >> (5 * shift)) & 0x1F]
        for shift in range(_ULID_LENGTH - 1, -1, -1)
    )
    return CaptureUid(encoded)


def format_capture_label(captured_at: datetime) -> str:
    return require_utc_datetime(captured_at, label="capture_label time").strftime(
        "%Y-%m-%dT%H-%M-%SZ"
    )


def is_capture_uid(value: str) -> bool:
    return len(value) == _ULID_LENGTH and all(
        character in _ULID_PATTERN for character in value
    )


@dataclass(frozen=True)
class CaptureIdentity:
    capture_uid: CaptureUid
    capture_label: str

    def __post_init__(self) -> None:
        if not is_capture_uid(str(self.capture_uid)):
            raise ValueError("capture_uid must be a ULID")
        if not self.capture_label.strip():
            raise ValueError("capture_label must not be blank")
