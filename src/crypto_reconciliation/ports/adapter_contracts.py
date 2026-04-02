"""Shared adapter contract metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from crypto_reconciliation.domain.types import AdapterId


class AdapterCapability(StrEnum):
    OUTPUT_RENDER = "output_render"
    INTAKE_ROUTE = "intake_route"
    SOURCE_TRANSLATE = "source_translate"
    WALLET_INVENTORY = "wallet_inventory"


@dataclass(frozen=True)
class AdapterManifest:
    adapter_id: AdapterId
    display_name: str
    version: str
    capabilities: frozenset[AdapterCapability]
    supported: bool = True
    description: str = ""
