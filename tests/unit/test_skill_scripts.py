from __future__ import annotations

import pytest

from tests.support.skill_scripts import load_skill_main


def test_load_skill_main_returns_callable_for_repo_skill_script() -> None:
    main = load_skill_main(
        ".agents/skills/balance-submission-operations/scripts/balance_submission_operations.py"
    )

    assert callable(main)


def test_load_skill_main_requires_existing_repo_skill_script() -> None:
    with pytest.raises(FileNotFoundError):
        load_skill_main(".agents/skills/missing/scripts/nope.py")
