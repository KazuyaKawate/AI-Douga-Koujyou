OS_VERSION = "5.2"
OS_CODENAME = "Google Workspace Sync Foundation"

APP_NAME = "Creator Factory OS"


def get_version_label() -> str:
    return f"v{OS_VERSION} — {OS_CODENAME}"


def get_app_title() -> str:
    return f"{APP_NAME} {get_version_label()}"
