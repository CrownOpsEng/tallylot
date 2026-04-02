"""NEAR export file-family classification."""

from __future__ import annotations

import re
from pathlib import Path

from tallylot.adapters.support import matching_file_paths, read_csv_header
from tallylot.domain.types import AdapterId
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry

_TIME_FIELDS = frozenset({"Time", "Block Time"})
_NEAR_ACCOUNT_PATTERN = re.compile(r"[a-z0-9_.-]{2,64}\.near|[a-f0-9]{32,64}")


def classify_inventory_families(
    inventory: tuple[FileInventoryEntry, ...],
    *,
    adapter_id: AdapterId,
) -> tuple[FileFamilyClaim, ...]:
    claims: list[FileFamilyClaim] = []
    for entry in inventory:
        family_id = family_id_for_header(entry.header)
        if not family_id:
            continue
        claims.append(
            FileFamilyClaim(
                relative_path=entry.relative_path,
                adapter_id=adapter_id,
                family_id=family_id,
            )
        )
    return tuple(claims)


def classified_csv_paths(raw_dir: Path) -> tuple[tuple[Path, str], ...]:
    classified: list[tuple[Path, str]] = []
    for path in matching_file_paths(raw_dir):
        family_id = family_id_for_header(read_csv_header(path))
        if family_id:
            classified.append((path, family_id))
    return tuple(classified)


def family_id_for_header(header: tuple[str, ...]) -> str:
    header_fields = set(header)
    if _TIME_FIELDS.isdisjoint(header_fields):
        return ""
    if {"Txn Hash", "Method", "Deposit Value", "Txn Fee"}.issubset(header_fields):
        return "base_transactions"
    if {"Receipt", "Txn Hash", "Method", "Deposit Value"}.issubset(header_fields):
        return "receipts"
    if {"Txn Hash", "Method", "Affected", "Involved", "Direction", "Quantity", "Token", "Contract"}.issubset(
        header_fields
    ):
        return "ft_transactions"
    if {"Txn Hash", "Method", "Affected", "Involved", "Direction", "Token ID", "Contract"}.issubset(header_fields):
        return "nft_transactions"
    return ""


def near_account_for_path(path: Path) -> str:
    name = path.name
    marker = next(
        (
            suffix
            for suffix in (
                "_transactions_",
                "_transactions.csv",
                "_receipts_",
                "_receipts.csv",
                "_ft_transactions_",
                "_ft_transactions.csv",
                "_nft_transactions_",
                "_nft_transactions.csv",
            )
            if suffix in name
        ),
        "",
    )
    prefix = name.split(marker, 1)[0] if marker else ""
    candidate = prefix.rsplit(" - ", 1)[-1].strip()
    return next((item.group(0) for item in _NEAR_ACCOUNT_PATTERN.finditer(candidate)), "")
