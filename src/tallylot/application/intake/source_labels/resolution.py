"""Source-label resolution for intake plan rows."""

from __future__ import annotations

from tallylot.application.intake.inventory import (
    InventoryRouteDecision,
    resolve_inventory_route,
)
from tallylot.application.intake.path_rules import is_source_scoped_target_path
from tallylot.ports.artifacts import ArtifactStorePort

from .models import (
    SourceLabelConfigIssue,
    SourceLabelContext,
    SourceLabelResolution,
    SourceLabelResolutionRequest,
    SourceLabelRule,
)


def resolve_source_label(
    *,
    artifacts: ArtifactStorePort,
    context: SourceLabelContext,
    request: SourceLabelResolutionRequest,
) -> SourceLabelResolution:
    if not is_source_scoped_target_path(
        request.target_path,
        workspace_root=request.workspace_root,
        source_folder=request.source_folder,
    ):
        return _non_source_scoped_resolution(request.source_folder)
    explicit_issue = _matching_issue(
        context.issues, request.incoming_capture_scope, request.route_key
    )
    explicit_rule = _matching_rule(
        context.rules, request.incoming_capture_scope, request.route_key
    )
    if explicit_issue is not None and (
        explicit_rule is None
        or _rule_priority(explicit_issue) >= _rule_priority(explicit_rule)
    ):
        return _blocked_resolution(request.source_folder, explicit_issue)
    if explicit_rule is not None:
        return _explicit_rule_resolution(explicit_rule)
    inventory_route = resolve_inventory_route(
        artifacts=artifacts,
        workspace_root=request.workspace_root,
        source_folder=request.source_folder,
        facts=request.facts,
    )
    return _inventory_or_routed_resolution(request.source_folder, inventory_route)


def _non_source_scoped_resolution(source_folder: str) -> SourceLabelResolution:
    return SourceLabelResolution(
        source_folder=source_folder,
        source_resolution_status="routed_source"
        if source_folder != "unclassified"
        else "routed_unclassified",
        source_resolution_reason=(
            f"Non-source-scoped destination keeps routed source {source_folder}."
            if source_folder != "unclassified"
            else "Non-source-scoped destination keeps routed unclassified source."
        ),
        inventory_match_status="unmatched",
    )


def _blocked_resolution(
    source_folder: str,
    issue: SourceLabelConfigIssue,
) -> SourceLabelResolution:
    return SourceLabelResolution(
        source_folder=source_folder,
        source_resolution_status="explicit_map_blocked",
        source_resolution_reason=issue.message,
        inventory_match_status="not_evaluated_explicit_map",
        review_required="yes",
        review_codes=issue.review_code,
        review_reason=issue.message,
        blocked=True,
    )


def _explicit_rule_resolution(rule: SourceLabelRule) -> SourceLabelResolution:
    scope_context = (
        f" within incoming capture scope {rule.incoming_capture_scope!r}"
        if rule.incoming_capture_scope
        else ""
    )
    return SourceLabelResolution(
        source_folder=rule.source,
        source_resolution_status="explicit_map",
        source_resolution_reason=(
            f"Explicit source map matched prefix {rule.prefix}{scope_context} -> {rule.source}"
        ),
        inventory_match_status="not_evaluated_explicit_map",
    )


def _inventory_or_routed_resolution(
    source_folder: str,
    inventory_route: InventoryRouteDecision,
) -> SourceLabelResolution:
    status = inventory_route.inventory_match_status
    if status == "inventory_source_match":
        return SourceLabelResolution(
            source_folder=inventory_route.source_folder,
            source_resolution_status="inventory_source_match",
            source_resolution_reason=(
                "Wallet evidence matched existing inventory source "
                f"{inventory_route.source_folder}"
            ),
            inventory_match_status=status,
        )
    if status == "inventory_source_ambiguous":
        return SourceLabelResolution(
            source_folder=inventory_route.source_folder,
            source_resolution_status="inventory_source_ambiguous",
            source_resolution_reason=inventory_route.review_reason,
            inventory_match_status=status,
            review_required=inventory_route.review_required,
            review_codes=inventory_route.review_codes,
            review_reason=inventory_route.review_reason,
        )
    if status == "generic_scope_routing":
        return SourceLabelResolution(
            source_folder=inventory_route.source_folder,
            source_resolution_status="generic_scope_routing",
            source_resolution_reason=(
                f"Generated source label {inventory_route.source_folder} "
                "from wallet scope evidence."
            ),
            inventory_match_status=status,
        )
    return SourceLabelResolution(
        source_folder=source_folder,
        source_resolution_status="routed_source"
        if source_folder != "unclassified"
        else "routed_unclassified",
        source_resolution_reason=(
            "Fell back to routed source "
            f"{source_folder} from adapter or file-signature matching."
            if source_folder != "unclassified"
            else "No explicit or inferred source match; using unclassified."
        ),
        inventory_match_status=status,
    )


def _matching_issue(
    issues: tuple[SourceLabelConfigIssue, ...],
    incoming_capture_scope: str,
    route_key: str,
) -> SourceLabelConfigIssue | None:
    matching_issues = [
        issue
        for issue in issues
        if issue.matching_prefix
        and _scope_matches(issue.incoming_capture_scope, incoming_capture_scope)
        and _prefix_matches(issue.matching_prefix, route_key)
    ]
    if not matching_issues:
        return None
    matching_issues.sort(
        key=lambda item: (
            1 if item.incoming_capture_scope else 0,
            len(item.matching_prefix),
            item.incoming_capture_scope,
            item.matching_prefix,
        ),
        reverse=True,
    )
    return matching_issues[0]


def _matching_rule(
    rules: tuple[SourceLabelRule, ...],
    incoming_capture_scope: str,
    route_key: str,
) -> SourceLabelRule | None:
    for rule in rules:
        if _scope_matches(rule.incoming_capture_scope, incoming_capture_scope) and (
            _prefix_matches(rule.prefix, route_key)
        ):
            return rule
    return None


def _prefix_matches(prefix: str, route_key: str) -> bool:
    if prefix == ".":
        return True
    if route_key == prefix:
        return True
    if not route_key.startswith(prefix):
        return False
    next_character = route_key[len(prefix) : len(prefix) + 1]
    return next_character in {"/", ":"}


def _scope_matches(scope: str, incoming_capture_scope: str) -> bool:
    return not scope or scope == incoming_capture_scope


def _rule_priority(
    rule: SourceLabelConfigIssue | SourceLabelRule,
) -> tuple[int, int]:
    return (
        1 if rule.incoming_capture_scope else 0,
        len(rule.matching_prefix)
        if isinstance(rule, SourceLabelConfigIssue)
        else len(rule.prefix),
    )
