"""Runtime balance provider registry assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from tallylot.domain.balances import BalanceProviderRequest
from tallylot.ports.balance_providers import BalanceProviderPort

from ..adapters.modules import iter_discoverable_modules


@dataclass(frozen=True)
class BalanceProviderRegistry:
    providers: tuple[BalanceProviderPort, ...]

    def provider_for_requests(
        self,
        requests: tuple[BalanceProviderRequest, ...],
    ) -> BalanceProviderPort | None:
        if not requests:
            return None
        for provider in self.providers:
            if all(provider.supports_target(request) for request in requests):
                return provider
        return None


def build_balance_provider_registry() -> BalanceProviderRegistry:
    return BalanceProviderRegistry(
        providers=_collect_balance_providers(
            "tallylot.adapters.balance_providers.providers"
        )
    )


def _collect_balance_providers(package_name: str) -> tuple[BalanceProviderPort, ...]:
    discovered: list[BalanceProviderPort] = []
    for module in iter_discoverable_modules(package_name):
        provider = getattr(module, "ADAPTER", None)
        if provider is None:
            continue
        discovered.append(_validate_balance_provider(provider, module.__name__))
    _validate_unique_provider_families(discovered)
    return tuple(sorted(discovered, key=lambda item: item.provider_family))


def _validate_balance_provider(
    provider: object,
    module_name: str,
) -> BalanceProviderPort:
    provider_family = getattr(provider, "provider_family", None)
    if not isinstance(provider_family, str) or not provider_family.strip():
        raise TypeError(f"{module_name} ADAPTER is missing provider_family")
    if not callable(getattr(provider, "supports_target", None)):
        raise TypeError(f"{module_name} ADAPTER is missing supports_target")
    if not callable(getattr(provider, "fetch_references", None)):
        raise TypeError(f"{module_name} ADAPTER is missing fetch_references")
    return cast(BalanceProviderPort, provider)


def _validate_unique_provider_families(
    providers: list[BalanceProviderPort],
) -> None:
    seen: set[str] = set()
    for provider in providers:
        if provider.provider_family in seen:
            raise ValueError(
                f"duplicate balance provider_family discovered: {provider.provider_family}"
            )
        seen.add(provider.provider_family)
