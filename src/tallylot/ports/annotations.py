"""Typed sidecar annotation records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tallylot.domain.types import JsonValue

_NAMESPACE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")


def _empty_values() -> dict[str, JsonValue]:
    return {}


@dataclass(frozen=True)
class AdapterMetadata:
    namespace: str
    values: dict[str, JsonValue] = field(default_factory=_empty_values)

    def __post_init__(self) -> None:
        if not _NAMESPACE_PATTERN.fullmatch(self.namespace):
            raise ValueError(
                "adapter metadata namespace must be lowercase dot-separated snake_case"
            )
