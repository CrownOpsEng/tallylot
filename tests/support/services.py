from __future__ import annotations

from typing import Any

from crypto_reconciliation.domain.types import AdapterId, SourceId
from crypto_reconciliation.ports.source_profiles import SourceProfile


def build_source_profile(
    *,
    adapter_id: str,
    source: str = "fixture",
    raw_dir: str = "/tmp/raw",
    **profile_fields: Any,
) -> SourceProfile:
    metadata = profile_fields.pop("metadata", {})
    normalization_hints = profile_fields.pop("normalization_hints", {})
    timezone_summary = profile_fields.pop("timezone_summary", {})
    return SourceProfile(
        source=SourceId(source),
        raw_dir=raw_dir,
        adapter_id=AdapterId(adapter_id),
        manifest_fingerprint="fixture",
        file_inventory=(),
        supported=True,
        metadata=metadata,
        normalization_hints=normalization_hints,
        timezone_summary=timezone_summary,
        **profile_fields,
    )
