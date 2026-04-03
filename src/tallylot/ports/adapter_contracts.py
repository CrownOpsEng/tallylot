"""Shared adapter contract metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from tallylot.domain.types import AdapterId


class AdapterCapability(StrEnum):
    LOCATION_INVENTORY = "location_inventory"
    OUTPUT_RENDER = "output_render"
    INTAKE_ROUTE = "intake_route"
    SOURCE_TRANSLATE = "source_translate"


@dataclass(frozen=True)
class AdapterManifest:
    adapter_id: AdapterId
    display_name: str
    version: str
    capabilities: frozenset[AdapterCapability]
    supported: bool = True
    description: str = ""
