"""Environment-driven settings for the live (non-demo) server runs.

Demos and tests construct servers directly with explicit paths and fake
backends; these settings only steer ``ai-mcp run``. Copy ``.env.example``
to ``.env`` to change them.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_MCP_", env_file=".env", extra="ignore")

    notes_dir: Path = Path("mcp-notes")
    crm_path: Path = Path(".ai-mcp-crm.json")
    fetch_allowlist: str = ""

    @property
    def allowlist(self) -> list[str]:
        """The web-fetch domain allowlist, parsed from a comma list."""
        return [part.strip() for part in self.fetch_allowlist.split(",") if part.strip()]


def get_settings() -> Settings:
    return Settings()
