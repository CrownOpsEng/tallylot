"""Routing models for intake decisions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
