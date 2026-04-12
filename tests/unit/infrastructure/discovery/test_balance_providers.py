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


def _request(
    *,
    location_id: str,
    instrument_id: str = "asset:evm:ethereum:native",
) -> BalanceProviderRequest:
    return BalanceProviderRequest(
        target=BalanceTarget(
            source=SourceId("wallet"),
            location_id=LocationId(location_id),
            instrument_id=InstrumentId(instrument_id),
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


def test_balance_provider_registry_discovers_provider_family_stubs() -> None:
    balance_registry = registry.build_balance_provider_registry()

    assert [provider.provider_family for provider in balance_registry.providers] == [
        "evm_json_rpc",
        "near_rpc",
    ]


def test_balance_provider_registry_routes_targets_by_family() -> None:
    balance_registry = registry.build_balance_provider_registry()
    evm_target = _request(
        location_id="evm:ethereum:0x1111111111111111111111111111111111111111",
        instrument_id="asset:evm:ethereum:erc20:0x4444444444444444444444444444444444444444",
    )
    near_target = _request(
        location_id="near:example.near",
        instrument_id="asset:near:native",
    )

    evm_provider = balance_registry.provider_for_requests((evm_target,))
    near_provider = balance_registry.provider_for_requests((near_target,))
    mixed_provider = balance_registry.provider_for_requests((evm_target, near_target))

    assert evm_provider is not None
    assert evm_provider.provider_family == "evm_json_rpc"
    assert near_provider is not None
    assert near_provider.provider_family == "near_rpc"
    assert mixed_provider is None


def test_balance_provider_stubs_return_explicit_unavailable_results() -> None:
    balance_registry = registry.build_balance_provider_registry()
    evm_target = _request(
        location_id="evm:polygon:0x2222222222222222222222222222222222222222",
        instrument_id="asset:evm:polygon:native",
    )
    provider = balance_registry.provider_for_requests((evm_target,))
    assert provider is not None

    result = provider.fetch_references((evm_target,))

    assert len(result) == 1
    assert result[0].target == evm_target.target
    assert result[0].issue_kind == "balance_provider_unavailable"
