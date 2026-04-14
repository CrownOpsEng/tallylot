from __future__ import annotations

from collections.abc import Sequence

from repo_support.pyright_config import (
    PYRIGHT_GENERATED_TEST_CONFIG_NAME,
    PYRIGHT_LOCAL_CONFIG_NAME,
    ensure_pyright_local_config,
    sync_pyright_config,
)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    generated_updated = sync_pyright_config()
    local_updated = ensure_pyright_local_config()
    status_lines = [
        (
            f"updated {PYRIGHT_GENERATED_TEST_CONFIG_NAME}"
            if generated_updated
            else f"{PYRIGHT_GENERATED_TEST_CONFIG_NAME} already in sync"
        ),
        (
            f"updated {PYRIGHT_LOCAL_CONFIG_NAME}"
            if local_updated
            else f"{PYRIGHT_LOCAL_CONFIG_NAME} already in sync"
        ),
    ]
    print("\n".join(status_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
