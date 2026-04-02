"""Output adapter ports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tallylot.domain.transactions import FactLegPolicy, TransactionFact
from tallylot.ports.adapter_contracts import AdapterManifest


@dataclass(frozen=True)
class RenderedArtifact:
    path: Path
    row_count: int
    metadata: dict[str, str]


@dataclass(frozen=True)
class OutputRenderPolicy:
    shape_policy: FactLegPolicy
    requires_projection_hint: bool


class OutputAdapter(Protocol):
    manifest: AdapterManifest
    render_policy: OutputRenderPolicy

    def render(
        self,
        facts: tuple[TransactionFact, ...],
        output_path: Path,
    ) -> RenderedArtifact: ...


class OutputAdapterRegistryPort(Protocol):
    @property
    def output_adapters(self) -> tuple[OutputAdapter, ...]: ...

    def output_adapter(self, adapter_id: str) -> OutputAdapter: ...
