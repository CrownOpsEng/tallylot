"""Application request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceInitRequest:
    workspace_root: Path


@dataclass(frozen=True)
class WorkspaceInitResponse:
    workspace_root: Path
    created_paths: tuple[Path, ...]


@dataclass(frozen=True)
class ManifestRequest:
    source_dir: Path
    output_path: Path


@dataclass(frozen=True)
class ManifestResponse:
    output_path: Path
    file_count: int
    manifest_fingerprint: str


@dataclass(frozen=True)
class ProfileRequest:
    source: str
    raw_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class ProfileResponse:
    output_dir: Path
    adapter_id: str
    file_count: int
    supported: bool


@dataclass(frozen=True)
class NormalizeRequest:
    source: str
    raw_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class NormalizeResponse:
    output_dir: Path
    adapter_id: str
    event_count: int
    balance_count: int
    issue_count: int
    review_count: int


@dataclass(frozen=True)
class WalletInventoryRequest:
    normalized_root: Path
    output_path: Path


@dataclass(frozen=True)
class WalletInventoryResponse:
    output_path: Path
    wallet_count: int


@dataclass(frozen=True)
class RenderCoinTrackingRequest:
    canonical_events_path: Path
    output_path: Path


@dataclass(frozen=True)
class RenderCoinTrackingResponse:
    output_path: Path
    row_count: int


@dataclass(frozen=True)
class VerificationCompareRequest:
    previous_dir: Path
    current_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class VerificationCompareResponse:
    output_dir: Path
    changed_reports: int


@dataclass(frozen=True)
class BaselineValidateRequest:
    export_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class BaselineValidateResponse:
    output_dir: Path
    latest_timestamp: str
    asset_count: int


@dataclass(frozen=True)
class StageBatchRequest:
    candidate_path: Path
    baseline_export_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class StageBatchResponse:
    output_dir: Path
    staged: bool
    duplicate_count: int
