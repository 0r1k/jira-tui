# Copyright (c) 2026 or1k.net
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "jira-tui"
CONFIG_FILE = CONFIG_DIR / "config.json"


class JiraConfig:
    def __init__(self, jira_url: str = "", email: str = "", api_token: str = "",
                 auth_type: str = "cloud"):
        self.jira_url = jira_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.auth_type = auth_type  # "cloud" or "server"

    @property
    def name(self) -> str:
        """Domain label without scheme, e.g. 'spalah-general.atlassian.net'."""
        url = self.jira_url
        for prefix in ("https://", "http://"):
            if url.startswith(prefix):
                url = url[len(prefix):]
        return url.rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.jira_url and self.api_token)

    def to_dict(self) -> dict:
        return {
            "jira_url": self.jira_url,
            "email": self.email,
            "api_token": self.api_token,
            "auth_type": self.auth_type,
        }


class MultiConfig:
    def __init__(self):
        self.jiras: list[JiraConfig] = []

    def load(self) -> bool:
        if not CONFIG_FILE.exists():
            return False
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            if "jiras" in data:
                self.jiras = [
                    JiraConfig(
                        jira_url=j.get("jira_url", ""),
                        email=j.get("email", ""),
                        api_token=j.get("api_token", ""),
                        auth_type=j.get("auth_type", "cloud"),
                    )
                    for j in data["jiras"]
                    if j.get("jira_url")
                ]
            elif "jira_url" in data:
                # Migrate from old single-jira format
                cfg = JiraConfig(
                    jira_url=data.get("jira_url", ""),
                    email=data.get("email", ""),
                    api_token=data.get("api_token", ""),
                    auth_type=data.get("auth_type", "cloud"),
                )
                if cfg.is_configured():
                    self.jiras = [cfg]
            return self.is_configured()
        except Exception:
            return False

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"jiras": [j.to_dict() for j in self.jiras]}, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)

    def is_configured(self) -> bool:
        return any(j.is_configured() for j in self.jiras)

    def add_or_update(self, cfg: JiraConfig) -> None:
        for i, existing in enumerate(self.jiras):
            if existing.jira_url == cfg.jira_url:
                self.jiras[i] = cfg
                return
        self.jiras.append(cfg)

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.jiras):
            self.jiras.pop(index)
