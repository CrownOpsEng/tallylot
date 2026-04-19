from __future__ import annotations

from .rules.contract_lock_contracts import CONTRACT_LOCK_CONTRACT_RULES
from .rules.contract_lock_matrix import CONTRACT_LOCK_MATRIX_RULES
from .rules.contract_lock_roadmap import CONTRACT_LOCK_ROADMAP_RULES
from .rules.policy_alignment import POLICY_ALIGNMENT_RULES
from .rules.routes import ROUTE_RULES
from .rules.runtime import RUNTIME_RULES


ALL_RULES = (
    *ROUTE_RULES,
    *RUNTIME_RULES,
    *POLICY_ALIGNMENT_RULES,
    *CONTRACT_LOCK_MATRIX_RULES,
    *CONTRACT_LOCK_CONTRACT_RULES,
    *CONTRACT_LOCK_ROADMAP_RULES,
)
RULES_BY_ID = {rule.rule_id: rule for rule in ALL_RULES}


def docs_audit_rule_ids() -> tuple[str, ...]:
    return tuple(rule.rule_id for rule in ALL_RULES)
