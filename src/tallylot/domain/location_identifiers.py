"""Shared location identifier parsing and normalization."""

from __future__ import annotations

import re

from tallylot.domain.types import LocationId

EVM_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
BTC_XPUB_PATTERN = re.compile(r"xpub[1-9A-HJ-NP-Za-km-z]+")
TRON_ADDRESS_PATTERN = re.compile(r"T[1-9A-HJ-NP-Za-km-z]{33}")
BTC_ADDRESS_PATTERN = re.compile(r"(bc1[ac-hj-np-z02-9]{11,71}|[13][1-9A-HJ-NP-Za-km-z]{25,34})")
SOLANA_ADDRESS_PATTERN = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
CARDANO_ACCOUNT_KEY_PATTERN = re.compile(r"[a-fA-F0-9]{64,}")

_IDENTIFIER_PATTERNS = (
    ("btc_xpub", BTC_XPUB_PATTERN),
    ("evm_address", EVM_ADDRESS_PATTERN),
    ("tron_address", TRON_ADDRESS_PATTERN),
    ("btc_address", BTC_ADDRESS_PATTERN),
    ("solana_address", SOLANA_ADDRESS_PATTERN),
)
_SCOPE_NETWORKS = {
    "btc_xpub": "btc",
    "btc_address": "btc",
    "cardano_account_key": "cardano",
    "evm_address": "evm",
    "solana_address": "solana",
    "tron_address": "tron",
}
_CANONICAL_LOCATION_NAMESPACES = {
    "btc_xpub": "bitcoin",
    "btc_address": "bitcoin",
    "cardano_account_key": "cardano",
    "near_account": "near",
    "solana_address": "solana",
    "tron_address": "tron",
}
_ONCHAIN_LOCATION_PREFIXES = ("evm:", "near:", "bitcoin:", "cardano:", "solana:", "tron:")


def normalized_identifier(identifier_kind: str, identifier_value: str) -> str:
    normalized = identifier_value.strip()
    if identifier_kind in {"evm_address", "address_alias"}:
        return normalized.lower()
    return normalized


def identifier_kind_for_value(identifier_value: str) -> str:
    value = identifier_value.strip()
    for identifier_kind, pattern in _IDENTIFIER_PATTERNS:
        if pattern.fullmatch(value):
            return identifier_kind
    if CARDANO_ACCOUNT_KEY_PATTERN.fullmatch(value):
        return "cardano_account_key"
    if re.fullmatch(r"[a-z0-9_.-]{6,64}", value):
        return "near_account"
    return "unknown"


def scope_token_for_identifier(identifier_value: str) -> str:
    identifier_kind = identifier_kind_for_value(identifier_value)
    network = _SCOPE_NETWORKS.get(identifier_kind)
    if network is None:
        return ""
    return f"{network}:{normalized_identifier(identifier_kind, identifier_value)}"


def canonical_location_id_from_identifier(
    identifier_kind: str,
    identifier_value: str,
    *,
    network_scope: str = "",
    suffix: tuple[str, ...] = (),
) -> LocationId:
    normalized_value = normalized_identifier(identifier_kind, identifier_value)
    parts: tuple[str, ...]
    if identifier_kind == "evm_address":
        normalized_scope = network_scope.strip().lower()
        if not normalized_scope:
            raise ValueError("canonical EVM location ids require a network scope")
        parts = ("evm", normalized_scope, normalized_value)
    else:
        namespace = _CANONICAL_LOCATION_NAMESPACES.get(identifier_kind)
        if namespace is None:
            raise ValueError(f"unsupported canonical location identifier kind: {identifier_kind}")
        parts = (namespace, normalized_value)
    normalized_suffix = tuple(_normalized_location_segment(item) for item in suffix if item.strip())
    return LocationId(":".join((*parts, *normalized_suffix)))


def is_onchain_canonical_location_id(location_id: str) -> bool:
    return location_id.startswith(_ONCHAIN_LOCATION_PREFIXES)


def _normalized_location_segment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
