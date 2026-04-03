"""Initialize the external workspace layout."""

from __future__ import annotations

from tallylot.application.resource_refs import path_from_ref, workspace_paths_from_paths
from tallylot.application.workspace.contracts import WorkspaceInitRequest, WorkspaceInitResponse
from tallylot.ports.workspace import WorkspaceRepository


class InitializeWorkspaceUseCase:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    def execute(self, request: WorkspaceInitRequest) -> WorkspaceInitResponse:
        created = self._repository.initialize(path_from_ref(request.workspace_root_ref))
        return WorkspaceInitResponse(
            workspace_root_ref=request.workspace_root_ref,
            created_refs=workspace_paths_from_paths(created),
        )
