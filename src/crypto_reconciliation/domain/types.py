"""Typed identifiers and shared aliases."""

from __future__ import annotations

from typing import NewType

AdapterId = NewType("AdapterId", str)
AssetSymbol = NewType("AssetSymbol", str)
EventId = NewType("EventId", str)
SourceId = NewType("SourceId", str)
WorkspacePath = NewType("WorkspacePath", str)
