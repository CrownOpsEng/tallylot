"""File-fact models for intake inspection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntakeFileFacts:
    header: tuple[str, ...] = ()
    min_timestamp: str = ""
    max_timestamp: str = ""
    scope_tokens: tuple[str, ...] = ()
    network_hints: tuple[str, ...] = ()
