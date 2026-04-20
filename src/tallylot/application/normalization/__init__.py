"""Normalization capability."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from .assembly import AssembleSourceUseCase
from .contracts import (
    AssembleSourceRequest,
    AssembleSourceResponse,
    NormalizeRequest,
    NormalizeResponse,
)
from .window import (
    filter_drafts_by_window,
    filter_issues_by_window,
    filter_reviews_by_window,
)

if TYPE_CHECKING:
    from .normalize_source import NormalizationDependencies, NormalizeSourceUseCase

__all__ = [
    "NormalizationDependencies",
    "AssembleSourceRequest",
    "AssembleSourceResponse",
    "AssembleSourceUseCase",
    "NormalizeRequest",
    "NormalizeResponse",
    "NormalizeSourceUseCase",
    "filter_drafts_by_window",
    "filter_issues_by_window",
    "filter_reviews_by_window",
]


def __getattr__(name: str) -> object:
    if name in {"NormalizationDependencies", "NormalizeSourceUseCase"}:
        module = import_module(".normalize_source", __name__)

        return {
            "NormalizationDependencies": module.NormalizationDependencies,
            "NormalizeSourceUseCase": module.NormalizeSourceUseCase,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
