from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .catalog_loader import (
    mapping_sequence_value as _mapping_sequence_value,
    optional_sequence_value as _optional_sequence_value,
    sequence_value as _sequence_value,
    string_tuple as _string_tuple,
    string_value as _string_value,
)


@dataclass(frozen=True)
class ProductFamily:
    name: str
    id: str


@dataclass(frozen=True)
class RecordFamily:
    stem: str
    record: str
    id: str
    refs: tuple[str, ...]


@dataclass(frozen=True)
class DirectoryFamily:
    stem: str
    sidecars: tuple[str, ...] = ()

    def directory_path(self, *, root: str) -> str:
        return f"{root}/{self.stem}/"

    def sidecar_paths(self, *, root: str) -> tuple[str, ...]:
        return tuple(f"{root}/{self.stem}/{sidecar}" for sidecar in self.sidecars)


@dataclass(frozen=True)
class DirectoryFamilyGroup:
    root: str
    families: tuple[DirectoryFamily, ...]


@dataclass(frozen=True)
class CanonicalFamilySet:
    products: tuple[ProductFamily, ...]
    records: tuple[RecordFamily, ...]
    package_paths: tuple[str, ...]
    standalone_directory_paths: tuple[str, ...]
    directory_groups: tuple[DirectoryFamilyGroup, ...]

    @property
    def directory_paths(self) -> tuple[str, ...]:
        grouped_paths = tuple(
            family.directory_path(root=group.root)
            for group in self.directory_groups
            for family in group.families
        )
        return (*self.standalone_directory_paths, *grouped_paths)

    @property
    def sidecar_paths(self) -> tuple[str, ...]:
        return tuple(
            sidecar_path
            for group in self.directory_groups
            for family in group.families
            for sidecar_path in family.sidecar_paths(root=group.root)
        )


def load_canonical_families(
    loaded: Mapping[object, object],
) -> CanonicalFamilySet:
    return CanonicalFamilySet(
        products=tuple(
            ProductFamily(
                name=_string_value(item, "name"),
                id=_string_value(item, "id"),
            )
            for item in _mapping_sequence_value(loaded, "products")
        ),
        records=tuple(
            RecordFamily(
                stem=_string_value(item, "stem"),
                record=_string_value(item, "record"),
                id=_string_value(item, "id"),
                refs=_string_tuple(_optional_sequence_value(item, "refs")),
            )
            for item in _mapping_sequence_value(loaded, "records")
        ),
        package_paths=_string_tuple(_sequence_value(loaded, "package_paths")),
        standalone_directory_paths=_string_tuple(
            _optional_sequence_value(loaded, "standalone_directory_paths")
        ),
        directory_groups=tuple(
            DirectoryFamilyGroup(
                root=_normalized_directory_root(_string_value(item, "root")),
                families=tuple(
                    DirectoryFamily(
                        stem=_string_value(family, "stem"),
                        sidecars=_string_tuple(
                            _optional_sequence_value(family, "sidecars")
                        ),
                    )
                    for family in _mapping_sequence_value(item, "families")
                ),
            )
            for item in _mapping_sequence_value(loaded, "directory_families")
        ),
    )


def validate_canonical_families(
    families: CanonicalFamilySet,
) -> tuple[str, ...]:
    errors: list[str] = []
    errors.extend(
        _duplicate_value_errors(
            (product.name for product in families.products),
            label="canonical product name",
        )
    )
    errors.extend(
        _duplicate_value_errors(
            (product.id for product in families.products),
            label="canonical product id",
        )
    )
    errors.extend(
        _duplicate_value_errors(
            (record.stem for record in families.records),
            label="canonical record stem",
        )
    )
    errors.extend(
        _duplicate_value_errors(
            (record.record for record in families.records),
            label="canonical record family",
        )
    )
    errors.extend(
        _duplicate_value_errors(
            (record.id for record in families.records),
            label="canonical record id",
        )
    )
    errors.extend(
        _duplicate_value_errors(
            (_product_directory_stem(product.name) for product in families.products),
            label="canonical product directory stem",
        )
    )
    errors.extend(
        _validate_directory_paths(
            products=families.products,
            records=families.records,
            standalone_paths=families.standalone_directory_paths,
            groups=families.directory_groups,
        )
    )
    return tuple(errors)


def _validate_directory_paths(
    *,
    products: tuple[ProductFamily, ...],
    records: tuple[RecordFamily, ...],
    standalone_paths: tuple[str, ...],
    groups: tuple[DirectoryFamilyGroup, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    product_directory_stems = {
        _product_directory_stem(product.name) for product in products
    }
    record_stems = {record.stem for record in records}
    errors.extend(
        _duplicate_value_errors(
            standalone_paths,
            label="standalone directory path",
        )
    )
    seen_directory_paths: set[str] = set()
    for path in standalone_paths:
        if not path:
            errors.append("standalone directory path must not be empty")
        if not path.endswith("/"):
            errors.append(f"standalone directory path must end with '/': {path!r}")
        seen_directory_paths.add(path)
    errors.extend(
        _duplicate_value_errors(
            (group.root for group in groups),
            label="directory family root",
        )
    )
    seen_sidecar_paths: set[str] = set()
    for group in groups:
        if not group.root:
            errors.append("directory family root must not be empty")
        family_stems = tuple(family.stem for family in group.families)
        errors.extend(
            _duplicate_value_errors(
                family_stems,
                label=f"directory family stem under {group.root}",
            )
        )
        errors.extend(
            _group_family_alignment_errors(
                group=group,
                family_stems=frozenset(family_stems),
                product_directory_stems=product_directory_stems,
            )
        )
        for family in group.families:
            errors.extend(
                _family_path_errors(
                    family=family,
                    root=group.root,
                    record_stems=record_stems,
                    seen_directory_paths=seen_directory_paths,
                    seen_sidecar_paths=seen_sidecar_paths,
                )
            )
    return tuple(errors)


def _family_path_errors(
    *,
    family: DirectoryFamily,
    root: str,
    record_stems: set[str],
    seen_directory_paths: set[str],
    seen_sidecar_paths: set[str],
) -> tuple[str, ...]:
    errors: list[str] = []
    if not family.stem or "/" in family.stem:
        errors.append(f"invalid directory family stem under {root}: {family.stem!r}")
    if any(sidecar.endswith("_records.json") for sidecar in family.sidecars) and (
        family.stem not in record_stems
    ):
        errors.append(
            "directory family stem must name a canonical record when it carries "
            f"record sidecars under {root}: {family.stem!r}"
        )
    directory_path = family.directory_path(root=root)
    if directory_path in seen_directory_paths:
        errors.append(f"duplicate canonical directory path: {directory_path}")
    seen_directory_paths.add(directory_path)
    for sidecar in family.sidecars:
        errors.extend(
            _sidecar_errors(
                family=family,
                directory_path=directory_path,
                sidecar=sidecar,
                record_stems=record_stems,
                seen_sidecar_paths=seen_sidecar_paths,
            )
        )
    return tuple(errors)


def _sidecar_errors(
    *,
    family: DirectoryFamily,
    directory_path: str,
    sidecar: str,
    record_stems: set[str],
    seen_sidecar_paths: set[str],
) -> tuple[str, ...]:
    errors: list[str] = []
    if "/" in sidecar:
        errors.append(
            f"directory family sidecar must be a basename under "
            f"{directory_path}: {sidecar!r}"
        )
    if not sidecar.endswith(".json"):
        errors.append(f"directory family sidecar must end with .json: {sidecar!r}")
    if sidecar != f"{family.stem}.json" and not sidecar.startswith(f"{family.stem}_"):
        errors.append(
            f"directory family sidecar must stay grouped under the family stem "
            f"{family.stem!r}: {sidecar!r}"
        )
    record_stem = _record_stem_for_sidecar(sidecar)
    if record_stem is not None and record_stem not in record_stems:
        errors.append(
            "directory family sidecar must reference a canonical record stem: "
            f"{sidecar!r}"
        )
    sidecar_path = f"{directory_path}{sidecar}"
    if sidecar_path in seen_sidecar_paths:
        errors.append(f"duplicate canonical sidecar path: {sidecar_path}")
    seen_sidecar_paths.add(sidecar_path)
    return tuple(errors)


def _group_family_alignment_errors(
    *,
    group: DirectoryFamilyGroup,
    family_stems: frozenset[str],
    product_directory_stems: set[str],
) -> tuple[str, ...]:
    if group.root != "working/products":
        return ()
    missing = sorted(product_directory_stems - family_stems)
    extra = sorted(family_stems - product_directory_stems)
    errors: list[str] = []
    if missing:
        errors.append(
            "working/products directory families must cover every canonical "
            f"product stem; missing: {', '.join(missing)}"
        )
    if extra:
        errors.append(
            "working/products directory families must stay aligned with "
            f"canonical product stems; unexpected: {', '.join(extra)}"
        )
    return tuple(errors)


def _record_stem_for_sidecar(sidecar: str) -> str | None:
    suffix = "_records.json"
    if not sidecar.endswith(suffix):
        return None
    return sidecar.removesuffix(suffix)


def _product_directory_stem(name: str) -> str:
    stem = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return stem if stem.endswith("s") else f"{stem}s"


def _duplicate_value_errors(
    values: Iterable[str],
    *,
    label: str,
) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return tuple(f"duplicate {label}: {value}" for value in duplicates)


def _normalized_directory_root(value: str) -> str:
    return value.strip("/")


__all__ = [
    "CanonicalFamilySet",
    "DirectoryFamily",
    "DirectoryFamilyGroup",
    "ProductFamily",
    "RecordFamily",
    "load_canonical_families",
    "validate_canonical_families",
]
