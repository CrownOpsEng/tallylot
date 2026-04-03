"""Typed intake-routing contracts owned by source adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IntakeFileFacts:
    header: tuple[str, ...] = ()
    min_timestamp: str = ""
    max_timestamp: str = ""
    scope_tokens: tuple[str, ...] = ()
    network_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntakeRoutingRequest:
    relative_path: str
    file_path: Path
    incoming_dir: Path
    workspace_root: Path
    facts: IntakeFileFacts
    archive_source_path: str = ""
    archive_member_path: str = ""

    @property
    def route_key(self) -> str:
        if self.archive_member_path:
            return f"{self.archive_source_path}::{self.archive_member_path}"
        return self.relative_path


@dataclass(frozen=True)
class IntakeRoute:
    category: str
    role: str
    source_folder: str
    capture_id: str
    action: str
    target_path: Path
    inventory_match_status: str = "unmatched"
    review_required: str = "no"
    review_codes: str = ""
    review_reason: str = ""
