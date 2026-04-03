from __future__ import annotations

import json

import pytest

from tools.adapter_packs import AdapterPack, select_adapter_packs
from tools.refresh_adapter_goldens import (
    EXPECTED_NORMALIZATION_ARTIFACTS,
    EXPECTED_WALLET_ARTIFACTS,
    collect_pack_outputs,
)

ALL_PACKS = select_adapter_packs()
NORMALIZATION_PACKS = tuple(pack for pack in ALL_PACKS if pack.supports("normalize"))


def _pack_id(pack: AdapterPack) -> str:
    return pack.id


@pytest.mark.parametrize("pack", ALL_PACKS, ids=_pack_id)
def test_adapter_pack_wallet_outputs_match_expected_goldens(pack: AdapterPack) -> None:
    payloads = collect_pack_outputs(pack)

    for artifact_name in EXPECTED_WALLET_ARTIFACTS:
        expected_path = pack.expected_dir / f"{artifact_name}.json"
        expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))
        assert payloads[artifact_name] == expected_payload


@pytest.mark.parametrize("pack", NORMALIZATION_PACKS, ids=_pack_id)
def test_adapter_pack_normalization_outputs_match_expected_goldens(pack: AdapterPack) -> None:
    payloads = collect_pack_outputs(pack)
    normalization_summary = payloads["normalization_summary"]

    assert isinstance(normalization_summary, dict)
    assert normalization_summary["adapter_id"] == pack.expected_adapter
    for artifact_name in EXPECTED_NORMALIZATION_ARTIFACTS:
        expected_path = pack.expected_dir / f"{artifact_name}.json"
        expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))
        assert payloads[artifact_name] == expected_payload
