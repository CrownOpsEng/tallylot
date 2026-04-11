"""Discoverable EVM JSON-RPC balance provider stub."""

from __future__ import annotations

from tallylot.domain.balances import BalanceProviderRequest, BalanceProviderResult
from tallylot.domain.location_identifiers import EVM_ADDRESS_PATTERN


class _EvmJsonRpcBalanceProviderStub:
    provider_family = "evm_json_rpc"

    def supports_target(self, request: BalanceProviderRequest) -> bool:
        location_id = str(request.target.location_id)
        if not location_id.startswith("evm:"):
            return False
        parts = location_id.split(":", 2)
        if len(parts) != 3:
            return False
        network = parts[1].strip().lower()
        if not network:
            return False
        instrument_id = str(request.target.instrument_id)
        native_id = f"asset:evm:{network}:native"
        if instrument_id == native_id:
            return True
        erc20_prefix = f"asset:evm:{network}:erc20:"
        if not instrument_id.startswith(erc20_prefix):
            return False
        contract_address = instrument_id.removeprefix(erc20_prefix)
        return bool(EVM_ADDRESS_PATTERN.fullmatch(contract_address))

    def fetch_references(
        self,
        requests: tuple[BalanceProviderRequest, ...],
    ) -> tuple[BalanceProviderResult, ...]:
        return tuple(
            BalanceProviderResult(
                target=request.target,
                issue_kind="balance_provider_unavailable",
                issue_message=(
                    "Historical balance lookup is not yet implemented for the EVM JSON-RPC "
                    "provider family."
                ),
            )
            for request in requests
        )


ADAPTER = _EvmJsonRpcBalanceProviderStub()
