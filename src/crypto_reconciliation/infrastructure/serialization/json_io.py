"""JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.domain.types import JsonValue


def write_json(path: Path, payload: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
