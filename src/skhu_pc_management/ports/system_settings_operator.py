from __future__ import annotations

from typing import Protocol


class SystemSettingsOperator(Protocol):
    def set_default_wallpaper(self) -> None:
        """Apply the default Windows wallpaper."""

    def delete_edge_shortcuts(self) -> None:
        """Delete Edge desktop shortcuts and disable shortcut recreation policy."""

    def disable_password_expiration_for_all_users(self) -> None:
        """Disable password expiration for local users when possible."""
