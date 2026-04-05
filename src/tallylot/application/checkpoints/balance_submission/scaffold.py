"""Scaffold user-facing manual balance submission packages."""

from __future__ import annotations

from tallylot.application.checkpoints.contracts import (
    ScaffoldBalanceSubmissionRequest,
    ScaffoldBalanceSubmissionResponse,
)
from tallylot.application.resource_refs import path_from_ref, to_resource_ref
from tallylot.application.workspace.filesystem import ensure_directory
from tallylot.ports.artifacts import ArtifactStorePort

from .readme_template import render_balance_submission_readme
from .schema import (
    BALANCE_CONFIRMATIONS_EXAMPLE_FILENAME,
    BALANCE_CONFIRMATIONS_HEADER,
    BALANCES_EXAMPLE_FILENAME,
    BALANCES_HEADER,
    LOCATION_INVENTORY_EXAMPLE_FILENAME,
    LOCATION_INVENTORY_HEADER,
    README_FILENAME,
)


class ScaffoldBalanceSubmissionUseCase:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(
        self,
        request: ScaffoldBalanceSubmissionRequest,
    ) -> ScaffoldBalanceSubmissionResponse:
        submission_root = ensure_directory(path_from_ref(request.submission_root_ref))
        readme_path = submission_root / README_FILENAME
        readme_path.write_text(
            render_balance_submission_readme(request.source),
            encoding="utf-8",
        )
        self._artifacts.write_rows(
            submission_root / BALANCES_EXAMPLE_FILENAME,
            BALANCES_HEADER,
            (
                {
                    "source": request.source,
                    "account": "primary",
                    "wallet": "primary",
                    "instrument_id": "symbol:BTC@coinbase",
                    "quantity": "0.0",
                    "as_of_at": "2026-03-23",
                    "as_of_precision": "date",
                    "balance_kind": "available",
                    "notes": "Replace every example value with user-provided facts.",
                },
            ),
        )
        self._artifacts.write_rows(
            submission_root / BALANCE_CONFIRMATIONS_EXAMPLE_FILENAME,
            BALANCE_CONFIRMATIONS_HEADER,
            (
                {
                    "source": request.source,
                    "account": "primary",
                    "wallet": "primary",
                    "instrument_id": "symbol:BTC@coinbase",
                    "quantity": "0.0",
                    "as_of_at": "2026-03-23",
                    "as_of_precision": "date",
                    "balance_kind": "available",
                    "confirmation_kind": "external_support",
                    "support_ref": "statement.pdf#page=1",
                    "asserted_meaning": "Closing balance from the cited statement.",
                    "reviewed_by": "operator@example.com",
                    "reviewed_at": "2026-03-24 00:00:00",
                    "reason": "Needed for runtime reconciliation.",
                    "notes": "Point to the supporting material or leave support_ref blank for manual_assertion.",
                },
            ),
        )
        self._artifacts.write_rows(
            submission_root / LOCATION_INVENTORY_EXAMPLE_FILENAME,
            LOCATION_INVENTORY_HEADER,
            (
                {
                    "source": request.source,
                    "account": "primary",
                    "wallet": "primary",
                    "identifier_kind": "evm_address",
                    "identifier_value": "0x0000000000000000000000000000000000000000",
                    "network_scope": "ethereum",
                    "controller": "self_custody",
                    "confidence": "high",
                    "notes": "Optional. Include only when explicit identity facts are available.",
                },
            ),
        )
        return ScaffoldBalanceSubmissionResponse(
            source=request.source,
            submission_root_ref=request.submission_root_ref,
            readme_ref=to_resource_ref(readme_path),
            balances_example_ref=to_resource_ref(
                submission_root / BALANCES_EXAMPLE_FILENAME
            ),
            balance_confirmations_example_ref=to_resource_ref(
                submission_root / BALANCE_CONFIRMATIONS_EXAMPLE_FILENAME
            ),
            location_inventory_example_ref=to_resource_ref(
                submission_root / LOCATION_INVENTORY_EXAMPLE_FILENAME
            ),
        )
