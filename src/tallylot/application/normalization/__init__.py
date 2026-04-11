"""Normalization capability."""

from .assembly import AssembleSourceUseCase
from .contracts import (
    AssembleSourceRequest,
    AssembleSourceResponse,
    NormalizeRequest,
    NormalizeResponse,
)
from .normalize_source import NormalizationDependencies, NormalizeSourceUseCase
from .window import (
    filter_drafts_by_window,
    filter_issues_by_window,
    filter_reviews_by_window,
)

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
