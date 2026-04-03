from __future__ import annotations

from collections.abc import Sequence

from repo_support.pyright_config import PYRIGHT_GENERATED_TEST_CONFIG_NAME, sync_pyright_config


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    updated = sync_pyright_config()
    print(
        f"updated {PYRIGHT_GENERATED_TEST_CONFIG_NAME}"
        if updated
        else f"{PYRIGHT_GENERATED_TEST_CONFIG_NAME} already in sync"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
