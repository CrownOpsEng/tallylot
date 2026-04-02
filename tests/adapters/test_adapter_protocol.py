from __future__ import annotations

import pytest

from adapter_protocol import AdapterProtocol
from source_adapters import ADAPTERS


@pytest.mark.adapter
def test_all_registered_adapters_conform_to_protocol() -> None:
    assert ADAPTERS
    for adapter in ADAPTERS:
        assert isinstance(adapter, AdapterProtocol)
