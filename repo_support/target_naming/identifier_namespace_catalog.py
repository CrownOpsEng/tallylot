from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol, cast

from .catalog_loader import (
    mapping_sequence_value as _mapping_sequence_value,
    sequence_value as _sequence_value,
    string_tuple as _string_tuple,
    string_value as _string_value,
)

IdentifierNamespaceMode = Literal["canonical", "local_short"]
SUPPORTED_IDENTIFIER_NAMESPACE_MODES: frozenset[IdentifierNamespaceMode] = frozenset(
    {"canonical", "local_short"}
)
IdentifierSurfaceKind = Literal[
    "field_slot",
    "array_component",
    "qualified_field_suffix",
]
SUPPORTED_IDENTIFIER_SURFACE_KINDS: frozenset[IdentifierSurfaceKind] = frozenset(
    {
        "field_slot",
        "array_component",
        "qualified_field_suffix",
    }
)


@dataclass(frozen=True)
class LocalIdSlot:
    canonical_id: str
    slot: str


@dataclass(frozen=True)
class IdentifierContextRule:
    path: str
    section_path: tuple[str, ...]
    region_label: str
    surface_kind: IdentifierSurfaceKind
    mode: IdentifierNamespaceMode
    canonical_ids: tuple[str, ...]


class IdentifierNamespaceCatalog(Protocol):
    @property
    def root_file_scopes(self) -> Mapping[str, object]: ...

    @property
    def title_expectations(self) -> Mapping[str, str]: ...

    @property
    def local_id_slots(self) -> tuple[LocalIdSlot, ...]: ...

    @property
    def identifier_context_rules(self) -> tuple[IdentifierContextRule, ...]: ...

    @property
    def canonical_token_set(self) -> frozenset[str]: ...

    @property
    def canonical_stable_id_set(self) -> frozenset[str]: ...

    @property
    def local_id_slot_by_canonical_id(self) -> dict[str, str]: ...


def build_local_id_slots(loaded: Mapping[object, object]) -> tuple[LocalIdSlot, ...]:
    return tuple(
        LocalIdSlot(
            canonical_id=_string_value(item, "canonical_id"),
            slot=_string_value(item, "slot"),
        )
        for item in _mapping_sequence_value(loaded, "local_id_slots")
    )


def build_identifier_context_rules(
    loaded: Mapping[object, object],
) -> tuple[IdentifierContextRule, ...]:
    return tuple(
        IdentifierContextRule(
            path=_string_value(item, "path"),
            section_path=_string_tuple(_sequence_value(item, "section_path")),
            region_label=_string_value(item, "region_label"),
            surface_kind=cast(
                IdentifierSurfaceKind,
                _string_value(item, "surface_kind"),
            ),
            mode=cast(
                IdentifierNamespaceMode,
                _string_value(item, "mode"),
            ),
            canonical_ids=_string_tuple(_sequence_value(item, "canonical_ids")),
        )
        for item in _mapping_sequence_value(loaded, "identifier_context_rules")
    )


def validate_local_id_slots(catalog: IdentifierNamespaceCatalog) -> tuple[str, ...]:
    errors: list[str] = []
    seen_slots: set[str] = set()
    seen_canonical_ids: set[str] = set()
    canonical_tokens = catalog.canonical_token_set
    canonical_stable_ids = catalog.canonical_stable_id_set
    for slot in catalog.local_id_slots:
        if slot.slot == slot.canonical_id:
            errors.append(
                f"local id slot must differ from canonical stable id: {slot.slot}"
            )
        if slot.slot in seen_slots:
            errors.append(f"duplicate local id slot: {slot.slot}")
        seen_slots.add(slot.slot)
        if slot.canonical_id in seen_canonical_ids:
            errors.append(
                "canonical stable id must map to at most one local slot: "
                f"{slot.canonical_id}"
            )
        seen_canonical_ids.add(slot.canonical_id)
        if slot.canonical_id not in canonical_stable_ids:
            errors.append(
                "local id slot must target a canonical stable id token: "
                f"{slot.canonical_id}"
            )
        if slot.slot in canonical_tokens:
            errors.append(
                f"local id slot must not reuse a canonical stable id token: {slot.slot}"
            )
    return tuple(errors)


def validate_identifier_context_rules(
    catalog: IdentifierNamespaceCatalog,
) -> tuple[str, ...]:
    errors: list[str] = []
    declared_paths = frozenset(
        (*catalog.root_file_scopes.keys(), *catalog.title_expectations.keys())
    )
    declared_local_ids = frozenset(catalog.local_id_slot_by_canonical_id)
    seen_rules: set[
        tuple[
            str,
            tuple[str, ...],
            str,
            str,
            str,
            tuple[str, ...],
        ]
    ] = set()
    for rule in catalog.identifier_context_rules:
        if rule.path not in declared_paths:
            errors.append(
                f"identifier context rule references undeclared path: {rule.path}"
            )
        if not rule.section_path:
            errors.append(
                "identifier context rule must declare a non-empty section_path: "
                f"{rule.path}"
            )
        if rule.surface_kind not in SUPPORTED_IDENTIFIER_SURFACE_KINDS:
            errors.append(f"unsupported identifier surface kind: {rule.surface_kind}")
        if rule.mode not in SUPPORTED_IDENTIFIER_NAMESPACE_MODES:
            errors.append(f"unsupported identifier namespace mode: {rule.mode}")
        for canonical_id in rule.canonical_ids:
            if canonical_id not in declared_local_ids:
                errors.append(
                    "identifier context rule references undeclared canonical id: "
                    f"{canonical_id}"
                )
        signature = (
            rule.path,
            rule.section_path,
            rule.region_label,
            rule.surface_kind,
            rule.mode,
            rule.canonical_ids,
        )
        if signature in seen_rules:
            errors.append(
                "duplicate identifier context rule: "
                f"{rule.path} {rule.section_path} {rule.region_label!r} "
                f"{rule.surface_kind} {rule.mode} {rule.canonical_ids}"
            )
        seen_rules.add(signature)
    return tuple(errors)


__all__ = [
    "IdentifierContextRule",
    "IdentifierNamespaceMode",
    "IdentifierSurfaceKind",
    "LocalIdSlot",
    "build_identifier_context_rules",
    "build_local_id_slots",
    "validate_identifier_context_rules",
    "validate_local_id_slots",
]
