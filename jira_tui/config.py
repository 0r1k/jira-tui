import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "jira-tui"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Config:
    def __init__(self):
        self.jira_url: str = ""
        self.email: str = ""
        self.api_token: str = ""
        self.auth_type: str = "cloud"  # "cloud" or "server"
        self.default_project: str = ""

    def load(self) -> bool:
        if not CONFIG_FILE.exists():
            return False
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            self.jira_url = data.get("jira_url", "").rstrip("/")
            self.email = data.get("email", "")
            self.api_token = data.get("api_token", "")
            self.auth_type = data.get("auth_type", "cloud")
            self.default_project = data.get("default_project", "")
            return self.is_configured()
        except Exception:
            return False

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "jira_url": self.jira_url,
                "email": self.email,
                "api_token": self.api_token,
                "auth_type": self.auth_type,
                "default_project": self.default_project,
            }, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)

    def is_configured(self) -> bool:
        return bool(self.jira_url and self.api_token)
