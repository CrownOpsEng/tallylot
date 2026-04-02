"""Normalization service."""

from __future__ import annotations

from crypto_reconciliation.application.dtos import NormalizeRequest, NormalizeResponse
from crypto_reconciliation.application.services.common import ensure_directory
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.ports.adapters import SourceAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.storage import StoragePort


class NormalizationService:
    def __init__(
        self,
        registry: SourceAdapterRegistryPort,
        profile_service: ProfileService,
        storage: StoragePort,
        artifacts: ArtifactStorePort,
    ) -> None:
        self._registry = registry
        self._profile_service = profile_service
        self._storage = storage
        self._artifacts = artifacts

    def execute(self, request: NormalizeRequest) -> NormalizeResponse:
        ensure_directory(request.output_dir)
        profile = self._profile_service.create_profile(request.source, request.raw_dir)
        self._profile_service.write_profile_artifacts(profile, request.output_dir)
        adapter = self._registry.source_adapter(str(profile.adapter_id))
        if not profile.supported:
            raise ValueError(
                f"source adapter {profile.adapter_id} "
                "is not supported for normalization in this phase"
            )
        result = adapter.normalize(profile, request.raw_dir)
        self._storage.write_canonical_events(
            request.output_dir / "canonical_events.csv",
            result.canonical_events,
        )
        self._storage.write_canonical_balances(
            request.output_dir / "canonical_balances.csv",
            result.canonical_balances,
        )
        self._storage.write_issue_records(request.output_dir / "exceptions.csv", result.issues)
        self._artifacts.write_rows(
            request.output_dir / "wallet_inventory.csv",
            (
                "wallet_id",
                "source",
                "account",
                "wallet",
                "evidence_path",
                "identifier_kind",
                "identifier_value",
                "notes",
            ),
            (record.to_row() for record in result.wallet_inventory),
        )
        self._artifacts.write_json(
            request.output_dir / "normalization_summary.json",
            {
                "source": request.source,
                "adapter_id": str(profile.adapter_id),
                "event_count": len(result.canonical_events),
                "balance_count": len(result.canonical_balances),
                "issue_count": len(result.issues),
                "wallet_count": len(result.wallet_inventory),
            },
        )
        return NormalizeResponse(
            output_dir=request.output_dir,
            adapter_id=str(profile.adapter_id),
            event_count=len(result.canonical_events),
            balance_count=len(result.canonical_balances),
            issue_count=len(result.issues),
        )
