from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from repo_support.paths import repo_root

from .catalog_loader import (
    bool_value as _bool_value,
    int_value as _int_value,
    mapping_mapping as _mapping_mapping,
    mapping_sequence as _mapping_sequence,
    mapping_sequence_value as _mapping_sequence_value,
    mapping_value as _mapping_value,
    optional_sequence_value as _optional_sequence_value,
    sequence_value as _sequence_value,
    string_mapping as _string_mapping,
    string_tuple as _string_tuple,
    string_value as _string_value,
)
from .model import MarkerLabel, NamingScope

SUPPORTED_REQUIRED_MARKERS: frozenset[MarkerLabel] = frozenset(
    {
        "Slice-only example",
        "Compatibility-only locality",
        "Current runtime note",
        "Anti-example",
        "Exception rationale",
        "Migration-only root rationale",
        "Locality rule",
    }
)


@dataclass(frozen=True)
class ScopeProfile:
    scope: NamingScope
    enforce_target_naming: bool
    allow_anti_examples: bool


@dataclass(frozen=True)
class CanonicalFamilySet:
    products: tuple[dict[str, str], ...]
    records: tuple[dict[str, object], ...]
    package_paths: tuple[str, ...]
    directory_paths: tuple[str, ...]
    sidecar_paths: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalTokenSet:
    pascal: tuple[str, ...]
    snake: tuple[str, ...]
    phrases: tuple[str, ...]


@dataclass(frozen=True)
class VocabularyCheck:
    path: str
    vocabulary: str
    label: str
    block_type: str
    expected_values: tuple[str, ...]


@dataclass(frozen=True)
class VocabularyCatalog:
    values: dict[str, tuple[str, ...]]
    paired_axes: tuple[tuple[str, ...], ...]
    checks: tuple[VocabularyCheck, ...]


@dataclass(frozen=True)
class PhraseRule:
    rule_id: str
    term: str
    contexts: tuple[str, ...]
    allowed_scopes: tuple[NamingScope, ...]
    paths: tuple[str, ...]


@dataclass(frozen=True)
class AliasRule:
    rule_id: str
    term: str
    replacement: str
    contexts: tuple[str, ...]
    allowed_scopes: tuple[NamingScope, ...]
    paths: tuple[str, ...]
    allowed_paths: tuple[str, ...]


@dataclass(frozen=True)
class MatrixSpec:
    path: str
    required_columns: tuple[str, ...]
    allowed_shape_nouns: tuple[str, ...]
    banned_fragments: tuple[str, ...]


@dataclass(frozen=True)
class ExceptionRule:
    exception_id: str
    allowed_scopes: tuple[NamingScope, ...]
    allowed_paths: tuple[str, ...]
    allowed_section_labels: tuple[str, ...]
    allowed_terms: tuple[str, ...]
    required_marker: MarkerLabel
    required_rationale: bool
    notes: str


@dataclass(frozen=True)
class TargetNamingCatalog:
    version: int
    root_file_scopes: dict[str, NamingScope]
    scope_profiles: dict[NamingScope, ScopeProfile]
    tooling_paths: tuple[str, ...]
    canonical_families: CanonicalFamilySet
    canonical_tokens: CanonicalTokenSet
    vocabularies: VocabularyCatalog
    banned_phrases: tuple[PhraseRule, ...]
    retired_aliases: tuple[AliasRule, ...]
    matrix_specs: tuple[MatrixSpec, ...]
    exceptions: tuple[ExceptionRule, ...]
    required_markers: tuple[MarkerLabel, ...]

    @property
    def canonical_token_set(self) -> frozenset[str]:
        tokens = set(self.canonical_tokens.pascal)
        tokens.update(self.canonical_tokens.snake)
        tokens.update(self.canonical_tokens.phrases)
        for product in self.canonical_families.products:
            tokens.update(product.values())
        for record in self.canonical_families.records:
            tokens.add(cast(str, record["record"]))
            tokens.add(cast(str, record["id"]))
            tokens.update(cast(tuple[str, ...], record.get("refs", ())))
        tokens.update(self.canonical_families.package_paths)
        tokens.update(self.canonical_families.directory_paths)
        tokens.update(self.canonical_families.sidecar_paths)
        for values in self.vocabularies.values.values():
            tokens.update(values)
        return frozenset(tokens)


def catalog_path() -> Path:
    return repo_root() / "tools" / "target_naming_catalog.yaml"


def load_target_naming_catalog(path: Path | None = None) -> TargetNamingCatalog:
    source = path or catalog_path()
    loaded: object = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise ValueError(f"{source} must contain a mapping")
    catalog = _build_catalog(cast(Mapping[object, object], loaded))
    errors = validate_target_naming_catalog(catalog)
    if errors:
        raise ValueError(f"invalid target naming catalog: {'; '.join(errors)}")
    return catalog


def validate_target_naming_catalog(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    errors: list[str] = []
    errors.extend(_validate_scope_profiles(catalog))
    errors.extend(_validate_required_markers(catalog))
    errors.extend(_validate_exceptions(catalog))
    errors.extend(_validate_paired_axes(catalog))
    errors.extend(_validate_rule_contexts(catalog))
    return tuple(errors)


def is_target_naming_tooling_path(
    path: str,
    *,
    catalog: TargetNamingCatalog | None = None,
) -> bool:
    loaded = catalog or load_target_naming_catalog()
    return (
        path.startswith("repo_support/target_naming/") or path in loaded.tooling_paths
    )


def _build_catalog(loaded: Mapping[object, object]) -> TargetNamingCatalog:
    root_file_scopes_loaded = _mapping_value(loaded, "root_file_scopes")
    scope_profiles_loaded = _mapping_value(loaded, "scope_profiles")
    canonical_families_loaded = _mapping_value(loaded, "canonical_families")
    canonical_tokens_loaded = _mapping_value(loaded, "canonical_tokens")
    vocabularies_loaded = _mapping_value(loaded, "vocabularies")
    return TargetNamingCatalog(
        version=_int_value(loaded, "version"),
        root_file_scopes={
            key: cast(NamingScope, value)
            for key, value in _string_mapping(root_file_scopes_loaded).items()
        },
        scope_profiles={
            cast(NamingScope, key): ScopeProfile(
                scope=cast(NamingScope, key),
                enforce_target_naming=_bool_value(value, "enforce_target_naming"),
                allow_anti_examples=_bool_value(value, "allow_anti_examples"),
            )
            for key, value in _mapping_mapping(scope_profiles_loaded).items()
        },
        tooling_paths=_string_tuple(_sequence_value(loaded, "tooling_paths")),
        canonical_families=CanonicalFamilySet(
            products=tuple(
                _string_mapping(item)
                for item in _mapping_sequence_value(
                    canonical_families_loaded, "products"
                )
            ),
            records=tuple(
                {
                    "stem": _string_value(item, "stem"),
                    "record": _string_value(item, "record"),
                    "id": _string_value(item, "id"),
                    "refs": _string_tuple(_optional_sequence_value(item, "refs")),
                }
                for item in _mapping_sequence_value(
                    canonical_families_loaded, "records"
                )
            ),
            package_paths=_string_tuple(
                _sequence_value(canonical_families_loaded, "package_paths")
            ),
            directory_paths=_string_tuple(
                _sequence_value(canonical_families_loaded, "directory_paths")
            ),
            sidecar_paths=_string_tuple(
                _sequence_value(canonical_families_loaded, "sidecar_paths")
            ),
        ),
        canonical_tokens=CanonicalTokenSet(
            pascal=_string_tuple(_sequence_value(canonical_tokens_loaded, "pascal")),
            snake=_string_tuple(_sequence_value(canonical_tokens_loaded, "snake")),
            phrases=_string_tuple(_sequence_value(canonical_tokens_loaded, "phrases")),
        ),
        vocabularies=_build_vocabulary_catalog(vocabularies_loaded),
        banned_phrases=tuple(
            PhraseRule(
                rule_id=_string_value(item, "rule_id"),
                term=_string_value(item, "term"),
                contexts=_string_tuple(_sequence_value(item, "contexts")),
                allowed_scopes=tuple(
                    cast(NamingScope, value)
                    for value in _string_tuple(_sequence_value(item, "allowed_scopes"))
                ),
                paths=_string_tuple(_sequence_value(item, "paths")),
            )
            for item in _mapping_sequence_value(loaded, "banned_phrases")
        ),
        retired_aliases=tuple(
            AliasRule(
                rule_id=_string_value(item, "rule_id"),
                term=_string_value(item, "term"),
                replacement=_string_value(item, "replacement"),
                contexts=_string_tuple(_sequence_value(item, "contexts")),
                allowed_scopes=tuple(
                    cast(NamingScope, value)
                    for value in _string_tuple(_sequence_value(item, "allowed_scopes"))
                ),
                paths=_string_tuple(_sequence_value(item, "paths")),
                allowed_paths=_string_tuple(_sequence_value(item, "allowed_paths")),
            )
            for item in _mapping_sequence_value(loaded, "retired_aliases")
        ),
        matrix_specs=tuple(
            MatrixSpec(
                path=_string_value(item, "path"),
                required_columns=_string_tuple(
                    _sequence_value(item, "required_columns")
                ),
                allowed_shape_nouns=_string_tuple(
                    _sequence_value(item, "allowed_shape_nouns")
                ),
                banned_fragments=_string_tuple(
                    _sequence_value(item, "banned_fragments")
                ),
            )
            for item in _mapping_sequence_value(loaded, "matrix_specs")
        ),
        exceptions=tuple(
            ExceptionRule(
                exception_id=_string_value(item, "exception_id"),
                allowed_scopes=tuple(
                    cast(NamingScope, value)
                    for value in _string_tuple(_sequence_value(item, "allowed_scopes"))
                ),
                allowed_paths=_string_tuple(_sequence_value(item, "allowed_paths")),
                allowed_section_labels=_string_tuple(
                    _sequence_value(item, "allowed_section_labels")
                ),
                allowed_terms=_string_tuple(_sequence_value(item, "allowed_terms")),
                required_marker=cast(
                    MarkerLabel, _string_value(item, "required_marker")
                ),
                required_rationale=_bool_value(item, "required_rationale"),
                notes=_string_value(item, "notes"),
            )
            for item in _mapping_sequence_value(loaded, "exceptions")
        ),
        required_markers=tuple(
            cast(MarkerLabel, value)
            for value in _string_tuple(_sequence_value(loaded, "required_markers"))
        ),
    )


def _build_vocabulary_catalog(loaded: Mapping[object, object]) -> VocabularyCatalog:
    values_mapping = _mapping_value(loaded, "values")
    checks_loaded = _mapping_sequence_value(loaded, "checks")
    return VocabularyCatalog(
        values={
            key: _string_tuple(value)
            for key, value in _mapping_sequence(values_mapping).items()
        },
        paired_axes=tuple(
            tuple(_string_tuple(cast(Sequence[object], item)))
            for item in _sequence_value(loaded, "paired_axes")
        ),
        checks=tuple(
            VocabularyCheck(
                path=_string_value(item, "path"),
                vocabulary=_string_value(item, "vocabulary"),
                label=_string_value(item, "label"),
                block_type=_string_value(item, "block_type"),
                expected_values=_string_tuple(_sequence_value(item, "expected_values")),
            )
            for item in checks_loaded
        ),
    )


def _validate_scope_profiles(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    errors: list[str] = []
    for scope, profile in catalog.scope_profiles.items():
        if scope != profile.scope:
            errors.append(f"scope profile key mismatch for {scope}")
    for root_path, scope in catalog.root_file_scopes.items():
        if not root_path.endswith(".md"):
            errors.append(f"root_file_scopes entry must be markdown: {root_path}")
        if scope not in catalog.scope_profiles:
            errors.append(f"unknown scope profile for root file {root_path}: {scope}")
    return tuple(errors)


def _validate_required_markers(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    return tuple(
        f"unsupported required marker {required_marker!r}"
        for required_marker in catalog.required_markers
        if required_marker not in SUPPORTED_REQUIRED_MARKERS
    )


def _validate_exceptions(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    errors: list[str] = []
    for exception in catalog.exceptions:
        if exception.required_marker not in catalog.required_markers:
            errors.append(
                f"exception {exception.exception_id} uses undeclared marker "
                f"{exception.required_marker!r}"
            )
        if not exception.allowed_paths and not exception.allowed_section_labels:
            errors.append(
                f"exception {exception.exception_id} must declare paths or sections"
            )
    return tuple(errors)


def _validate_paired_axes(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    errors: list[str] = []
    for vocabulary_names in catalog.vocabularies.paired_axes:
        seen: dict[str, str] = {}
        for vocabulary_name in vocabulary_names:
            values = catalog.vocabularies.values.get(vocabulary_name)
            if values is None:
                errors.append(f"unknown vocabulary in paired axis: {vocabulary_name}")
                continue
            for value in values:
                previous = seen.get(value)
                if previous is not None:
                    errors.append(
                        f"paired-axis overlap for {value}: {previous} and "
                        f"{vocabulary_name}"
                    )
                seen[value] = vocabulary_name
    return tuple(errors)


def _validate_rule_contexts(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    errors: list[str] = []
    for phrase in catalog.banned_phrases:
        if not phrase.contexts:
            errors.append(f"banned phrase {phrase.term!r} must declare contexts")
    for alias in catalog.retired_aliases:
        if not alias.contexts:
            errors.append(f"retired alias {alias.term!r} must declare contexts")
    return tuple(errors)


__all__ = [
    "AliasRule",
    "CanonicalFamilySet",
    "CanonicalTokenSet",
    "ExceptionRule",
    "MatrixSpec",
    "PhraseRule",
    "ScopeProfile",
    "TargetNamingCatalog",
    "VocabularyCatalog",
    "VocabularyCheck",
    "catalog_path",
    "is_target_naming_tooling_path",
    "load_target_naming_catalog",
    "validate_target_naming_catalog",
]
