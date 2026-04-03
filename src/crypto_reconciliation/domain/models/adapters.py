"""Adapter-facing domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from crypto_reconciliation.domain.types import AdapterId


class AdapterCapability(StrEnum):
    NORMALIZE = "normalize"
    WALLET_INVENTORY = "wallet_inventory"
    OUTPUT_RENDER = "output_render"
    REVIEW = "review"
    INTAKE_ROUTE = "intake_route"


@dataclass(frozen=True)
class AdapterManifest:
    adapter_id: AdapterId
    display_name: str
    version: str
    capabilities: frozenset[AdapterCapability]
    supported: bool = True
    description: str = ""
