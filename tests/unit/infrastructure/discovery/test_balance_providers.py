from __future__ import annotations

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from types import ModuleType
from typing import cast

import pytest

from tallylot.domain.balances import (
    BalanceProviderRequest,
    BalanceProviderResult,
    BalanceReference,
    BalanceReferenceKind,
    BalanceTarget,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.domain.instruments import InstrumentId
from tallylot.infrastructure.discovery.balance_providers import registry


class ProviderModule(ModuleType):
    ADAPTER: object | None = None  # pylint: disable=invalid-name


class ProviderFixture:
    provider_family = "fixture_provider"

    def supports_target(self, request: BalanceProviderRequest) -> bool:
        return str(request.target.location_id).startswith("evm:ethereum:")

    def fetch_references(
        self,
        requests: tuple[BalanceProviderRequest, ...],
    ) -> tuple[BalanceProviderResult, ...]:
        return tuple(
            BalanceProviderResult(
                target=request.target,
                reference=BalanceReference(
                    target=request.target,
                    quantity=Decimal("1"),
                    reference_kind=BalanceReferenceKind.NETWORK_API,
                    observed_at=request.target.target_at,
                    observed_precision=request.target.target_precision,
                    provider_family=self.provider_family,
                ),
            )
            for request in requests
        )


def _request(*, location_id: str) -> BalanceProviderRequest:
    return BalanceProviderRequest(
        target=BalanceTarget(
            source=SourceId("wallet"),
            location_id=LocationId(location_id),
            instrument_id=InstrumentId("asset:evm:ethereum:native"),
            balance_kind="available",
            target_at=datetime(2026, 3, 23, tzinfo=UTC),
            target_precision=TemporalPrecision.DATE,
        )
    )


def test_balance_provider_discovery_rejects_invalid_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ProviderModule("fixture.invalid_provider")

    class InvalidProvider:
        provider_family = ""

    module.ADAPTER = InvalidProvider()  # pylint: disable=invalid-name

    def fake_iter_discoverable_modules(package_name: str) -> tuple[ModuleType, ...]:
        del package_name
        return (cast(ModuleType, module),)

    monkeypatch.setattr(
        registry,
        "iter_discoverable_modules",
        fake_iter_discoverable_modules,
    )

    with pytest.raises(TypeError, match="missing provider_family"):
        registry._collect_balance_providers("fixture.providers")


def test_balance_provider_registry_routes_requests_by_supported_targets() -> None:
    provider = ProviderFixture()
    balance_registry = registry.BalanceProviderRegistry(providers=(provider,))

    matched = balance_registry.provider_for_requests(
        (
            _request(
                location_id="evm:ethereum:0x1111111111111111111111111111111111111111"
            ),
            _request(
                location_id="evm:ethereum:0x2222222222222222222222222222222222222222"
            ),
        )
    )
    unmatched = balance_registry.provider_for_requests(
        (_request(location_id="near:example.near"),)
    )

    assert matched is provider
    assert unmatched is None
