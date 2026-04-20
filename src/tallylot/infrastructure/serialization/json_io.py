"""JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path

from tallylot.domain.types import JsonValue


def write_json(path: Path, payload: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8"
    )
