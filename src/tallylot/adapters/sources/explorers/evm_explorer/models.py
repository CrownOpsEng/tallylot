"""EVM explorer translation models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvmTranslationContext:
    owned_addresses: set[str]
    network_scope: str
    blocked_tx_hashes: set[str]
    unsupported_methods: dict[str, str]
