"""Initialize the external workspace layout."""

from __future__ import annotations

from tallylot.application.workspace.contracts import WorkspaceInitRequest, WorkspaceInitResponse
from tallylot.ports.workspace import WorkspaceRepository


class InitializeWorkspaceUseCase:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    def execute(self, request: WorkspaceInitRequest) -> WorkspaceInitResponse:
        created = self._repository.initialize(request.workspace_root)
        return WorkspaceInitResponse(workspace_root=request.workspace_root, created_paths=created)
