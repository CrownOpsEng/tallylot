"""Ronin export file-family classification."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.support import matching_file_paths, read_csv_header
from tallylot.domain.types import AdapterId
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry

EXPLORER_HEADER = (
    "Txhash",
    "Blockno",
    "UnixTimestamp",
    "DateTime",
    "From",
    "To",
    "Method",
    "Token / Collectibles",
    "Value in",
    "Value out",
    "TxnFee(RON)",
    "Status",
)
SUMMARY_HEADER = (
    "RoninAddress",
    "TxnHash",
    "TxnURL",
    "Timestamp",
    "ActionType",
    "Actions",
    "AxieID",
    "AxieURL",
    "LandID",
    "ItemID",
    "ETH",
    "SLP",
    "AXS",
    "USDC",
    "¥/ETH",
    "¥/SLP",
    "¥/AXS",
    "AXS-WETH",
    "SLP-WETH",
    "USDC-WETH",
    "From",
    "To",
)


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
    if header == EXPLORER_HEADER:
        return "explorer_export"
    if header == SUMMARY_HEADER:
        return "action_summary"
    return ""
