"""Discoverable NEAR RPC balance provider stub."""

from __future__ import annotations

from tallylot.domain.balances import BalanceProviderRequest, BalanceProviderResult


class _NearRpcBalanceProviderStub:
    provider_family = "near_rpc"

    def supports_target(self, request: BalanceProviderRequest) -> bool:
        location_id = str(request.target.location_id)
        if not location_id.startswith("near:"):
            return False
        account = location_id.removeprefix("near:").strip()
        if not account:
            return False
        return str(request.target.instrument_id) == "asset:near:native"

    def fetch_references(
        self,
        requests: tuple[BalanceProviderRequest, ...],
    ) -> tuple[BalanceProviderResult, ...]:
        return tuple(
            BalanceProviderResult(
                target=request.target,
                issue_kind="balance_provider_unavailable",
                issue_message=(
                    "Historical balance lookup is not yet implemented for the NEAR RPC "
                    "provider family."
                ),
            )
            for request in requests
        )


ADAPTER = _NearRpcBalanceProviderStub()
