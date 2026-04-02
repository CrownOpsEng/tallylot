"""Stub generic HTTP output adapter entry point."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest, CanonicalEvent
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.ports.adapters import RenderedArtifact


class GenericHttpOutputStubAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("generic_http_output"),
        display_name="Generic HTTP Output",
        version="0.0.0",
        capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
        supported=False,
        description="Reserved HTTP output adapter entry point.",
    )

    def render(self, events: tuple[CanonicalEvent, ...], output_path: Path) -> RenderedArtifact:
        del events, output_path
        raise NotImplementedError("Generic HTTP output is intentionally stubbed in this phase.")


ADAPTER = GenericHttpOutputStubAdapter()
