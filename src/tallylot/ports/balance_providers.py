"""Balance provider ports."""

from __future__ import annotations

from typing import Protocol

from tallylot.domain.balances import BalanceProviderRequest, BalanceProviderResult


class BalanceProviderPort(Protocol):
    provider_family: str

    def supports_target(self, request: BalanceProviderRequest) -> bool: ...

    def fetch_references(
        self,
        requests: tuple[BalanceProviderRequest, ...],
    ) -> tuple[BalanceProviderResult, ...]: ...


class BalanceProviderRegistryPort(Protocol):
    @property
    def providers(self) -> tuple[BalanceProviderPort, ...]: ...

    def provider_for_requests(
        self,
        requests: tuple[BalanceProviderRequest, ...],
    ) -> BalanceProviderPort | None: ...
