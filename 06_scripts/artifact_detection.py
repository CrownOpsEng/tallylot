#!/usr/bin/env python3

"""Artifact detection rules kept separate from source/export classification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".jfif", ".gif", ".bmp", ".webp"}


@dataclass(frozen=True)
class ArtifactDecision:
    artifact_kind: str
    role: str
    review_required: bool
    review_code: str
    reason: str

    @property
    def review_codes(self) -> tuple[str, ...]:
        return (self.review_code,) if self.review_code else ()


def detect_artifact(relative_path: Path, inspection_row: dict[str, str]) -> ArtifactDecision | None:
    name = relative_path.name.lower()
    text = " / ".join(part.lower() for part in relative_path.parts)
    family = inspection_row.get("family", "")
    suffix = relative_path.suffix.lower()

    if suffix == ".xps":
        return ArtifactDecision("xps_document", "working_derivative", True, "unsupported_routing", "Unsupported XPS document; keep as supporting artifact.")
    if suffix in IMAGE_SUFFIXES:
        if "trade analysis" in name or "positions left open" in name or "margin calls" in name:
            return ArtifactDecision("analysis_image", "working_derivative", False, "", "Screenshot-style analysis artifact.")
        return ArtifactDecision("image_artifact", "working_derivative", True, "non_export_artifact", "Image artifact inside source dump.")
    if name == "test.csv":
        return ArtifactDecision("scratch_csv", "working_derivative", False, "", "Scratch/test CSV artifact.")
    if family == "mixed_portfolio_workbook":
        return ArtifactDecision("mixed_portfolio_workbook", "working_derivative", False, "", "User-assembled mixed workbook artifact.")
    return None
