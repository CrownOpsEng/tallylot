from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class DocsAuditFinding:
    rule_id: str
    path: str
    message: str
    suggestion: str | None = None


@dataclass(frozen=True)
class DocsAuditReport:
    requested_paths: tuple[str, ...]
    evaluated_rule_ids: tuple[str, ...]
    findings: tuple[DocsAuditFinding, ...]
    full_repo: bool
    evaluated_paths: tuple[str, ...]


@dataclass(frozen=True)
class DocsAuditRule:
    rule_id: str
    run: Callable[[], tuple[DocsAuditFinding, ...]]


RuleRunner = Callable[[], tuple[DocsAuditFinding, ...]]
