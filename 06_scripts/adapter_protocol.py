#!/usr/bin/env python3

"""Protocol for source adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pipeline_common import SourceProfile
from source_adapters import AdapterNormalizationResult


@runtime_checkable
class AdapterProtocol(Protocol):
    name: str
    supported: bool

    def validate_profile_timezones(self, profile: SourceProfile) -> tuple[dict[str, object], list[dict[str, str]]]:
        ...

    def extract_wallet_identifiers(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        ...

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        ...
