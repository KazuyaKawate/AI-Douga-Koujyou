"""src/workspace — Google Workspace Sync foundation for Creator Factory OS v5.2.

Manual sync only. No automatic execution. Dry-run enabled by default.
No external API calls are made automatically.
"""
VERSION = "5.2"
MODULE_TYPE = "utility"

from src.workspace.google_workspace import GoogleWorkspaceManager, get_google_workspace_health
from src.workspace.integration import GoogleService, GoogleWorkspaceIntegration, WorkspaceActionStore

__all__ = ["GoogleService", "GoogleWorkspaceManager", "get_google_workspace_health", "GoogleWorkspaceIntegration", "WorkspaceActionStore"]
