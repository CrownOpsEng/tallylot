"""Baseline validation workflow."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.dtos import BaselineValidateRequest, BaselineValidateResponse
from crypto_reconciliation.domain.models import AdapterCapability
from crypto_reconciliation.ports.adapters import OutputAdapter, OutputAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.output_workflows import BaselineArtifacts

ASSET_SNAPSHOT_HEADER = (
    "ticker",
    "current_balance_amount",
    "balance_by_exchange_amount",
    "difference",
)
EXCHANGE_RECONCILIATION_HEADER = (
    "ticker",
    "current_balance_amount",
    "balance_by_exchange_amount",
    "difference",
    "status",
)
NEGATIVE_BALANCE_HEADER = ("ticker", "name", "type", "amount", "value_cad")
SOURCE_ACTIVITY_HEADER = (
    "source",
    "first_trade_timestamp",
    "last_trade_timestamp",
    "trade_table_rows",
    "balance_by_exchange_rows",
    "balance_asset_count",
    "present_in_trade_table",
    "present_in_balance_by_exchange",
)
CAD_FLOW_HEADER = ("type", "cad_bought", "cad_sold", "cad_fees", "net_cad")
CAD_BALANCE_HEADER = ("exchange", "amount", "current_value_cad")


class BaselineValidationService:
    def __init__(self, registry: OutputAdapterRegistryPort, artifacts: ArtifactStorePort) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: BaselineValidateRequest) -> BaselineValidateResponse:
        adapter = _resolve_review_adapter(self._registry, request.export_dir, self._artifacts)
        artifacts = adapter.build_baseline_artifacts(request.export_dir, self._artifacts)
        request.output_dir.mkdir(parents=True, exist_ok=True)
        _write_baseline_artifacts(request.output_dir, artifacts, self._artifacts)
        return BaselineValidateResponse(
            output_dir=request.output_dir,
            latest_timestamp=str(artifacts.summary["latest_transaction_timestamp"]),
            asset_count=len(artifacts.reconciliation_rows),
        )


def _write_baseline_artifacts(
    output_dir: Path,
    artifacts: BaselineArtifacts,
    store: ArtifactStorePort,
) -> None:
    store.write_rows(output_dir / "baseline_asset_snapshot.csv", ASSET_SNAPSHOT_HEADER, artifacts.asset_snapshot_rows)
    store.write_rows(
        output_dir / "baseline_exchange_reconciliation.csv",
        EXCHANGE_RECONCILIATION_HEADER,
        artifacts.reconciliation_rows,
    )
    store.write_rows(
        output_dir / "baseline_negative_balances.csv",
        NEGATIVE_BALANCE_HEADER,
        artifacts.negative_balances,
    )
    store.write_rows(
        output_dir / "baseline_source_activity.csv",
        SOURCE_ACTIVITY_HEADER,
        artifacts.source_activity_rows,
    )
    store.write_rows(output_dir / "baseline_cad_flow_by_type.csv", CAD_FLOW_HEADER, artifacts.cad_flow_rows)
    store.write_rows(
        output_dir / "baseline_cad_balance_by_exchange.csv",
        CAD_BALANCE_HEADER,
        artifacts.cad_balance_by_exchange_rows,
    )
    store.write_json(output_dir / "baseline_summary.json", artifacts.summary)


def _resolve_review_adapter(
    registry: OutputAdapterRegistryPort,
    export_dir: Path,
    artifacts: ArtifactStorePort,
) -> OutputAdapter:
    matches = [
        (adapter.match_baseline_exports(export_dir, artifacts), adapter)
        for adapter in registry.output_adapters
        if adapter.manifest.supported and AdapterCapability.REVIEW in adapter.manifest.capabilities
    ]
    scored_matches = [(score, adapter) for score, adapter in matches if score > 0]
    if not scored_matches:
        raise ValueError(f"unable to detect supported baseline export adapter from {export_dir}")
    scored_matches.sort(key=lambda item: item[0], reverse=True)
    best_score = scored_matches[0][0]
    best_adapters = [adapter for score, adapter in scored_matches if score == best_score]
    if len(best_adapters) > 1:
        adapter_ids = ", ".join(sorted(str(adapter.manifest.adapter_id) for adapter in best_adapters))
        raise ValueError(f"ambiguous baseline export adapter: {adapter_ids}")
    return best_adapters[0]
