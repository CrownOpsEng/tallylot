from __future__ import annotations

import json

from tools.adapter_packs import select_adapter_packs
from tools.refresh_adapter_goldens import (
    EXPECTED_NORMALIZATION_ARTIFACTS,
    EXPECTED_WALLET_ARTIFACTS,
    collect_pack_outputs,
)


def test_adapter_packs_match_expected_goldens() -> None:
    packs = select_adapter_packs()

    for pack in packs:
        payloads = collect_pack_outputs(pack)
        if pack.supports("normalize"):
            normalization_summary = payloads["normalization_summary"]
            assert isinstance(normalization_summary, dict)
            assert normalization_summary["adapter_id"] == pack.expected_adapter
            for artifact_name in EXPECTED_NORMALIZATION_ARTIFACTS:
                expected_path = pack.expected_dir / f"{artifact_name}.json"
                expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))
                assert payloads[artifact_name] == expected_payload
        for artifact_name in EXPECTED_WALLET_ARTIFACTS:
            expected_path = pack.expected_dir / f"{artifact_name}.json"
            expected_payload = json.loads(expected_path.read_text(encoding="utf-8"))
            assert payloads[artifact_name] == expected_payload
