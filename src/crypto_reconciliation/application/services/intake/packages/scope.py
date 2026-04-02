"""Scope-compatibility helpers for intake package rules."""

from __future__ import annotations

from .models import BundlePackage


def compatible_scope(primary: BundlePackage, candidate: BundlePackage) -> bool:
    primary_material_scope = material_scope_tokens(primary.scope_tokens)
    candidate_material_scope = material_scope_tokens(candidate.scope_tokens)
    if primary_material_scope and candidate_material_scope:
        return bool(primary_material_scope & candidate_material_scope)
    if primary.scope_tokens and candidate.scope_tokens:
        return bool(primary.scope_tokens & candidate.scope_tokens)
    return True


def scope_status(primary: BundlePackage, candidate: BundlePackage) -> str:
    primary_material_scope = material_scope_tokens(primary.scope_tokens)
    candidate_material_scope = material_scope_tokens(candidate.scope_tokens)
    if primary_material_scope and candidate_material_scope:
        return "matched_scope" if primary_material_scope & candidate_material_scope else "incompatible_scope"
    if primary.scope_tokens and candidate.scope_tokens:
        return "matched_scope" if primary.scope_tokens & candidate.scope_tokens else "incompatible_scope"
    if primary.scope_tokens or candidate.scope_tokens:
        return "partial_scope"
    return "scope_unknown"


def material_scope_tokens(tokens: frozenset[str]) -> frozenset[str]:
    return frozenset(token for token in tokens if not token.startswith("label:"))


def overlap_reason(scope_status_value: str) -> str:
    if scope_status_value == "incompatible_scope":
        return "shared material but explicit scope identifiers differ"
    return "shared material but export-cycle markers or contents do not justify merge"
