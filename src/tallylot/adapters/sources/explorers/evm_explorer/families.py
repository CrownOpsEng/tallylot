"""EVM explorer file-family classification."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.support import matching_file_paths, read_csv_header
from tallylot.domain.types import AdapterId
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry

NATIVE_REQUIRED_FIELDS = {"Transaction Hash", "DateTime (UTC)", "To"}
TOKEN_REQUIRED_FIELDS = {"Transaction Hash", "DateTime (UTC)", "From", "To", "TokenValue", "TokenSymbol"}
NFT_REQUIRED_FIELDS = {"Transaction Hash", "DateTime (UTC)", "From", "To", "TokenName", "Token ID", "Quantity"}
NFT_MINIMUM_FIELDS = {"Transaction Hash", "To", "TokenName"}
INTERNAL_REQUIRED_FIELDS = {
    "Transaction Hash",
    "DateTime (UTC)",
    "ParentTxFrom",
    "ParentTxTo",
    "From",
    "TxTo",
}


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
    if TOKEN_REQUIRED_FIELDS.issubset(header_fields):
        return "token_transfers"
    if NFT_REQUIRED_FIELDS.issubset(header_fields) or NFT_MINIMUM_FIELDS.issubset(header_fields):
        return "nft_transfers"
    if INTERNAL_REQUIRED_FIELDS.issubset(header_fields) and _has_native_value_columns(header):
        return "internal_transfers"
    if NATIVE_REQUIRED_FIELDS.issubset(header_fields) and _has_native_value_columns(header):
        return "native_transfers"
    return ""


def native_symbol_for_header(header: tuple[str, ...]) -> str:
    for field in header:
        if field.startswith("Value_IN(") and field.endswith(")"):
            return field.removeprefix("Value_IN(").removesuffix(")")
    return ""


def _has_native_value_columns(header: tuple[str, ...]) -> bool:
    return any(field.startswith("Value_IN(") for field in header) or any(
        field.startswith("Value_OUT(") for field in header
    )
