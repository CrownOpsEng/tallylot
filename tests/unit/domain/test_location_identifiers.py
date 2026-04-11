from __future__ import annotations

import pytest

from tallylot.domain.location_identifiers import require_location_id


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    (
        ("coinbase:primary", "coinbase:primary"),
        ("near:example.near", "near:example.near"),
        (
            "evm:ethereum:0x1111111111111111111111111111111111111111",
            "evm:ethereum:0x1111111111111111111111111111111111111111",
        ),
        (
            "bitcoin:bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs",
            "bitcoin:bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq9e75rs",
        ),
    ),
)
def test_require_location_id_accepts_supported_location_id_forms(
    raw_value: str,
    expected: str,
) -> None:
    assert str(require_location_id(raw_value, label="location id")) == expected


@pytest.mark.parametrize(
    "raw_value",
    (
        "manual-balance-smoke:primary",
        "fixture:wallet-1",
        "crypto-com",
    ),
)
def test_require_location_id_rejects_hyphenated_generic_location_ids(
    raw_value: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="manual balance row location_id .*is not a supported location id",
    ):
        require_location_id(raw_value, label="manual balance row location_id")
