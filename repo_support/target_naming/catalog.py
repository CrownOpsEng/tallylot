from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

import yaml

from repo_support.paths import repo_root


@dataclass(frozen=True)
class PathScope:
    paths: tuple[str, ...]
    prefixes: tuple[str, ...]

    def matches(self, path: str) -> bool:
        return path in self.paths or any(
            path.startswith(prefix) for prefix in self.prefixes
        )


@dataclass(frozen=True)
class SurfaceCatalog:
    include: PathScope
    exclude: PathScope


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
    required_in: tuple[str, ...]

    @property
    def required_tokens(self) -> tuple[str, ...]:
        return (self.record, self.id, *self.refs)


@dataclass(frozen=True)
class PathFamilies:
    package_stems: tuple[str, ...]
    directory_stems: tuple[str, ...]
    sidecar_paths: tuple[str, ...]


@dataclass(frozen=True)
class TokenCatalog:
    pascal: tuple[str, ...]
    snake: tuple[str, ...]


@dataclass(frozen=True)
class VocabularyCheck:
    path: str
    vocabulary: str
    label: str
    block_type: str
    expected_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class VocabularyCatalog:
    values: dict[str, tuple[str, ...]]
    paired_axes: tuple[tuple[str, ...], ...]
    checks: tuple[VocabularyCheck, ...]


@dataclass(frozen=True)
class PhraseCatalog:
    canonical: tuple[str, ...]


@dataclass(frozen=True)
class BannedAlias:
    term: str
    replacement: str
    finding_class: str
    summary_only: bool
    paths: tuple[str, ...]
    path_prefixes: tuple[str, ...]

    def applies_to(self, path: str, *, summary_only: bool) -> bool:
        if self.summary_only and not summary_only:
            return False
        if self.paths or self.path_prefixes:
            return path in self.paths or any(
                path.startswith(prefix) for prefix in self.path_prefixes
            )
        return True


@dataclass(frozen=True)
class PathException:
    name: str
    paths: tuple[str, ...]
    path_prefixes: tuple[str, ...]
    allowed_terms: tuple[str, ...]

    def applies_to(self, path: str, term: str) -> bool:
        if term not in self.allowed_terms:
            return False
        return path in self.paths or any(
            path.startswith(prefix) for prefix in self.path_prefixes
        )


@dataclass(frozen=True)
class TargetNamingCatalog:
    version: int
    surfaces: SurfaceCatalog
    products: tuple[ProductFamily, ...]
    records: tuple[RecordFamily, ...]
    paths: PathFamilies
    tokens: TokenCatalog
    vocabularies: VocabularyCatalog
    phrases: PhraseCatalog
    aliases: tuple[BannedAlias, ...]
    exceptions: tuple[PathException, ...]

    @property
    def canonical_tokens(self) -> frozenset[str]:
        tokens: set[str] = set()
        for product in self.products:
            tokens.update((product.name, product.id))
        for record in self.records:
            tokens.update(record.required_tokens)
        tokens.update(self.paths.package_stems)
        tokens.update(self.paths.directory_stems)
        tokens.update(self.paths.sidecar_paths)
        tokens.update(self.tokens.pascal)
        tokens.update(self.tokens.snake)
        for values in self.vocabularies.values.values():
            tokens.update(values)
        tokens.update(self.phrases.canonical)
        return frozenset(tokens)

    @property
    def exception_terms(self) -> frozenset[str]:
        return frozenset(
            term for exception in self.exceptions for term in exception.allowed_terms
        )


TARGET_NAMING_TOOLING_PATHS = frozenset(
    {
        "Makefile",
        "docs/standards/delivery-guardrails.md",
        ".github/workflows/ci.yml",
        ".github/workflows/pr-review.yml",
        "repo_support/quality_gates.py",
        "repo_support/review_verification/catalog.py",
        "repo_support/review_verification/policy.py",
        "repo_support/review_verification/surfaces.py",
        "tools/audit_delivery_guardrails.py",
        "tools/docs_maintenance/metadata.py",
        "tools/target_naming.py",
        "tools/target_naming_catalog.yaml",
        "tests/contract/test_standards_guards.py",
        "tests/unit/docs_runtime_parity/test_repo_doc_guards.py",
        "tests/unit/test_audit_pr_review.py",
        "tests/unit/test_delivery_guardrails_audit.py",
        "tests/unit/test_docs_maintenance.py",
        "tests/unit/test_quality_gates.py",
        "tests/unit/test_review_verification_workflows.py",
        "tests/unit/test_run_pr_review_checks.py",
        "tests/unit/test_target_naming.py",
    }
)


def catalog_path() -> Path:
    return repo_root() / "tools" / "target_naming_catalog.yaml"


def load_target_naming_catalog(path: Path | None = None) -> TargetNamingCatalog:
    source = path or catalog_path()
    loaded: object = yaml.safe_load(source.read_text(encoding="utf-8"))
    catalog = _build_catalog(_normalize_mapping(loaded, str(source)))
    errors = validate_target_naming_catalog(catalog)
    if errors:
        raise ValueError(f"invalid target naming catalog: {'; '.join(errors)}")
    return catalog


def validate_target_naming_catalog(catalog: TargetNamingCatalog) -> tuple[str, ...]:
    errors: list[str] = []
    overlap = set(catalog.surfaces.include.paths).intersection(
        catalog.surfaces.exclude.paths
    )
    if overlap:
        errors.append(f"surface include/exclude overlap: {sorted(overlap)}")
    for prefix in (
        *catalog.surfaces.include.prefixes,
        *catalog.surfaces.exclude.prefixes,
    ):
        if not prefix.endswith("/"):
            errors.append(f"path prefix must end with '/': {prefix}")
    include_paths = set(catalog.surfaces.include.paths)
    for record in catalog.records:
        if record.required_in and any(
            path not in include_paths for path in record.required_in
        ):
            errors.append(
                f"record family {record.stem} uses required_in outside include surfaces"
            )
    for vocabulary_names in catalog.vocabularies.paired_axes:
        seen: dict[str, str] = {}
        for vocabulary_name in vocabulary_names:
            if vocabulary_name not in catalog.vocabularies.values:
                errors.append(f"unknown vocabulary in paired axis: {vocabulary_name}")
                continue
            for value in catalog.vocabularies.values[vocabulary_name]:
                previous = seen.get(value)
                if previous is not None:
                    errors.append(
                        f"paired-axis overlap for {value}: {previous} and {vocabulary_name}"
                    )
                seen[value] = vocabulary_name
    return tuple(errors)


def iter_target_naming_paths(
    catalog: TargetNamingCatalog | None = None,
) -> tuple[Path, ...]:
    loaded = catalog or load_target_naming_catalog()
    root = repo_root()
    return tuple(
        root / relative_path for relative_path in loaded.surfaces.include.paths
    )


def is_target_naming_sensitive_path(path: str) -> bool:
    catalog = load_target_naming_catalog()
    if catalog.surfaces.include.matches(path):
        return True
    if path.startswith("repo_support/target_naming/"):
        return True
    return path in TARGET_NAMING_TOOLING_PATHS


def _build_catalog(loaded: Mapping[str, object]) -> TargetNamingCatalog:
    families = _mapping_value(loaded, "families")
    paths = _mapping_value(families, "paths")
    tokens = _optional_mapping_value(loaded, "tokens")
    return TargetNamingCatalog(
        version=_int_value(loaded, "version"),
        surfaces=_surface_catalog(_mapping_value(loaded, "surfaces"), "surfaces"),
        products=tuple(
            ProductFamily(
                name=_string_value(item, "name"),
                id=_string_value(item, "id"),
            )
            for item in _mapping_sequence(families, "products")
        ),
        records=tuple(
            RecordFamily(
                stem=_string_value(item, "stem"),
                record=_string_value(item, "record"),
                id=_string_value(item, "id"),
                refs=_string_tuple(item.get("refs"), "refs"),
                required_in=_string_tuple(item.get("required_in"), "required_in"),
            )
            for item in _mapping_sequence(families, "records")
        ),
        paths=PathFamilies(
            package_stems=_string_tuple(paths.get("package_stems"), "package_stems"),
            directory_stems=_string_tuple(
                paths.get("directory_stems"), "directory_stems"
            ),
            sidecar_paths=_string_tuple(paths.get("sidecar_paths"), "sidecar_paths"),
        ),
        tokens=TokenCatalog(
            pascal=_string_tuple(tokens.get("pascal"), "tokens.pascal"),
            snake=_string_tuple(tokens.get("snake"), "tokens.snake"),
        ),
        vocabularies=_vocabulary_catalog(families),
        phrases=PhraseCatalog(
            canonical=_string_tuple(
                _mapping_value(loaded, "phrases").get("canonical"),
                "phrases.canonical",
            )
        ),
        aliases=tuple(
            BannedAlias(
                term=_string_value(item, "term"),
                replacement=_string_value(item, "replacement"),
                finding_class=_string_value(item, "finding_class"),
                summary_only=_bool_value(item.get("summary_only"), "summary_only"),
                paths=_string_tuple(item.get("paths"), "paths"),
                path_prefixes=_string_tuple(item.get("path_prefixes"), "path_prefixes"),
            )
            for item in _mapping_sequence(_mapping_value(loaded, "aliases"), "banned")
        ),
        exceptions=tuple(
            PathException(
                name=_string_value(item, "name"),
                paths=_string_tuple(item.get("paths"), "paths"),
                path_prefixes=_string_tuple(item.get("path_prefixes"), "path_prefixes"),
                allowed_terms=_string_tuple(item.get("allowed_terms"), "allowed_terms"),
            )
            for item in _mapping_sequence(loaded, "exceptions")
        ),
    )


def _surface_catalog(loaded: Mapping[str, object], context: str) -> SurfaceCatalog:
    return SurfaceCatalog(
        include=_path_scope(_mapping_value(loaded, "include"), f"{context}.include"),
        exclude=_path_scope(_mapping_value(loaded, "exclude"), f"{context}.exclude"),
    )


def _path_scope(loaded: Mapping[str, object], context: str) -> PathScope:
    return PathScope(
        paths=_string_tuple(loaded.get("paths"), f"{context}.paths"),
        prefixes=_string_tuple(loaded.get("prefixes"), f"{context}.prefixes"),
    )


def _vocabulary_catalog(families: Mapping[str, object]) -> VocabularyCatalog:
    vocabulary_root = _mapping_value(families, "vocabularies")
    raw_values = _mapping_value(vocabulary_root, "values")
    values = {
        key: _string_tuple(value, f"vocabulary {key}")
        for key, value in raw_values.items()
    }
    paired_axes = tuple(
        _string_tuple(entry, "paired_axes")
        for entry in _object_sequence(
            vocabulary_root.get("paired_axes"), "vocabularies.paired_axes"
        )
    )
    checks = tuple(
        VocabularyCheck(
            path=_string_value(item, "path"),
            vocabulary=_string_value(item, "vocabulary"),
            label=_string_value(item, "label"),
            block_type=_string_value(item, "block_type"),
            expected_values=_string_tuple(
                item.get("expected_values"), "expected_values"
            ),
        )
        for item in _mapping_sequence(vocabulary_root, "checks")
    )
    return VocabularyCatalog(values=values, paired_axes=paired_axes, checks=checks)


def _mapping_sequence(
    loaded: Mapping[str, object], key: str
) -> tuple[Mapping[str, object], ...]:
    current: object = loaded
    for part in key.split("."):
        mapping_current = _optional_normalize_mapping(current)
        if mapping_current is None or part not in mapping_current:
            return ()
        current = mapping_current[part]
    result: list[Mapping[str, object]] = []
    for item in _object_sequence(current, key):
        result.append(_normalize_mapping(item, key))
    return tuple(result)


def _mapping_value(loaded: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = loaded.get(key)
    return _normalize_mapping(value, key)


def _optional_mapping_value(
    loaded: Mapping[str, object], key: str
) -> Mapping[str, object]:
    value = loaded.get(key)
    if value is None:
        return {}
    return _normalize_mapping(value, key)


def _normalize_mapping(value: object, label: str) -> Mapping[str, object]:
    mapping = _optional_normalize_mapping(value)
    if mapping is None:
        raise ValueError(f"{label} must be a mapping")
    return mapping


def _optional_normalize_mapping(value: object) -> Mapping[str, object] | None:
    if not _is_object_mapping(value):
        return None
    normalized: dict[str, object] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            raise ValueError("mapping keys must be strings")
        normalized[raw_key] = raw_value
    return normalized


def _is_object_mapping(value: object) -> TypeGuard[Mapping[object, object]]:
    return isinstance(value, Mapping)


def _is_object_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _object_sequence(value: object, key: str) -> tuple[object, ...]:
    if value is None:
        return ()
    if not _is_object_list(value):
        raise ValueError(f"{key} must be a list")
    return tuple(value)


def _string_value(loaded: Mapping[str, object], key: str) -> str:
    value = loaded.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _int_value(loaded: Mapping[str, object], key: str) -> int:
    value = loaded.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _bool_value(value: object, key: str) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _string_tuple(value: object, key: str) -> tuple[str, ...]:
    result: list[str] = []
    for item in _object_sequence(value, key):
        if not isinstance(item, str) or not item:
            raise ValueError(f"{key} entries must be non-empty strings")
        result.append(item)
    return tuple(result)


__all__ = [
    "BannedAlias",
    "PathException",
    "PathFamilies",
    "PathScope",
    "PhraseCatalog",
    "ProductFamily",
    "RecordFamily",
    "SurfaceCatalog",
    "TARGET_NAMING_TOOLING_PATHS",
    "TargetNamingCatalog",
    "TokenCatalog",
    "VocabularyCatalog",
    "VocabularyCheck",
    "catalog_path",
    "is_target_naming_sensitive_path",
    "iter_target_naming_paths",
    "load_target_naming_catalog",
    "validate_target_naming_catalog",
]
