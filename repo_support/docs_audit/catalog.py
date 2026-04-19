from __future__ import annotations

from .rules.forward_contracts_contracts import FORWARD_CONTRACTS_CONTRACT_RULES
from .rules.forward_contracts_matrix import FORWARD_CONTRACTS_MATRIX_RULES
from .rules.policy_alignment import POLICY_ALIGNMENT_RULES
from .rules.routes import ROUTE_RULES
from .rules.runtime import RUNTIME_RULES


ALL_RULES = (
    *ROUTE_RULES,
    *RUNTIME_RULES,
    *POLICY_ALIGNMENT_RULES,
    *FORWARD_CONTRACTS_MATRIX_RULES,
    *FORWARD_CONTRACTS_CONTRACT_RULES,
)
RULES_BY_ID = {rule.rule_id: rule for rule in ALL_RULES}


def docs_audit_rule_ids() -> tuple[str, ...]:
    return tuple(rule.rule_id for rule in ALL_RULES)
