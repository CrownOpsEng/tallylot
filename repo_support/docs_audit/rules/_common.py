from __future__ import annotations

from collections.abc import Callable

from ..helpers import failure_finding
from ..model import DocsAuditFinding, DocsAuditRule, RuleRunner


def build_rule(
    rule_id: str,
    path: str,
    check: Callable[[], object],
) -> DocsAuditRule:
    def run() -> tuple[DocsAuditFinding, ...]:
        try:
            check()
        except AssertionError as error:
            return (failure_finding(rule_id, path, error),)
        return ()

    runner: RuleRunner = run
    return DocsAuditRule(rule_id=rule_id, run=runner)
