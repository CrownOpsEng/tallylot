"""Typed identifiers and shared aliases."""

from __future__ import annotations

from typing import NewType

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]

AdapterId = NewType("AdapterId", str)
AssetSymbol = NewType("AssetSymbol", str)
LocationId = NewType("LocationId", str)
TransactionId = NewType("TransactionId", str)
SourceId = NewType("SourceId", str)
WorkspacePath = NewType("WorkspacePath", str)
