"""Source-label resolution for intake planning."""

from .loading import load_source_label_context
from .models import (
    SourceLabelConfigIssue,
    SourceLabelContext,
    SourceLabelResolution,
    SourceLabelRule,
)
from .resolution import resolve_source_label

__all__ = [
    "SourceLabelConfigIssue",
    "SourceLabelContext",
    "SourceLabelResolution",
    "SourceLabelRule",
    "load_source_label_context",
    "resolve_source_label",
]
