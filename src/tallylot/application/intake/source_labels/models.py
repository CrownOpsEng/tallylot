"""Typed models for source-label resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tallylot.application.intake.file_facts import IntakeFileFacts


@dataclass(frozen=True)
class SourceLabelRule:
    prefix: str
    source: str


@dataclass(frozen=True)
class SourceLabelConfigIssue:
    relative_path: str
    severity: str
    kind: str
    message: str
    matching_prefix: str = ""
    review_code: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "relative_path": self.relative_path,
            "severity": self.severity,
            "kind": self.kind,
            "message": self.message,
        }


@dataclass(frozen=True)
class SourceLabelContext:
    rules: tuple[SourceLabelRule, ...]
    issues: tuple[SourceLabelConfigIssue, ...]


@dataclass(frozen=True)
class SourceLabelResolution:
    source_folder: str
    source_resolution_status: str
    source_resolution_reason: str
    inventory_match_status: str
    review_required: str = "no"
    review_codes: str = ""
    review_reason: str = ""
    blocked: bool = False


@dataclass(frozen=True)
class SourceLabelResolutionRequest:
    workspace_root: Path
    route_key: str
    facts: IntakeFileFacts
    source_folder: str
    target_path: Path
