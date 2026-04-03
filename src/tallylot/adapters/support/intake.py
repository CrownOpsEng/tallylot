"""Shared helpers for adapter-owned intake routing."""

from __future__ import annotations

from typing import cast

from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest


def match_intake_by_path_or_header(
    relative_path: str,
    facts: IntakeFileFacts,
    *,
    path_hints: tuple[str, ...] = (),
    header_hints: tuple[str, ...] = (),
) -> int:
    lower_path = relative_path.lower()
    if any(hint in lower_path for hint in path_hints):
        return 100
    normalized_header = ",".join(facts.header).strip().lower()
    if normalized_header and any(hint in normalized_header for hint in header_hints):
        return 100
    return 0


def no_intake_route(request: IntakeRoutingRequest) -> IntakeRoute | None:
    del request
    return cast(IntakeRoute | None, None)
