# Copyright (c) 2026 or1k.net
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.binding import Binding
from ..config import JiraConfig, MultiConfig
from ..client import JiraClient


class JiraListScreen(Screen):
    """Settings screen — list of configured Jira instances."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    CSS = """
    JiraListScreen { align: center middle; }
    #list-box {
        width: 72; height: auto; max-height: 40;
        border: round $accent; background: $surface; padding: 1 2;
    }
    #list-title {
        text-align: center; text-style: bold; color: $accent; margin-bottom: 1;
    }
    #jira-list { height: auto; max-height: 28; }
    .jira-row {
        height: 3; margin-bottom: 1;
    }
    .jira-name-btn {
        width: 1fr; height: 3; margin: 0;
        background: $panel; border: tall $panel; color: $text;
    }
    .jira-name-btn:hover { background: $accent; color: $background; }
    .jira-del-btn {
        width: 12; height: 3; margin: 0 0 0 1;
        background: $error; border: tall $error; color: $background;
    }
    .jira-del-btn:hover { background: $error-darken-1; }
    #empty-hint { color: $text-muted; text-align: center; padding: 1 0; }
    #bottom-row { height: 3; align: center middle; margin-top: 1; }
    """

    def __init__(self, multi_config: MultiConfig, **kwargs):
        super().__init__(**kwargs)
        self._multi_config = multi_config

    def compose(self) -> ComposeResult:
        with Container(id="list-box"):
            yield Static("⚙  Jira TUI © or1k.net — Connections", id="list-title")
            yield ScrollableContainer(id="jira-list")
            with Horizontal(id="bottom-row"):
                yield Button("Add Jira", variant="primary", id="add-btn")
                yield Button("Close [Esc]", variant="error", id="close-btn")

    def on_mount(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        container = self.query_one("#jira-list", ScrollableContainer)
        container.remove_children()
        if not self._multi_config.jiras:
            container.mount(Static("No Jira instances configured yet.", id="empty-hint"))
            return
        for idx, jcfg in enumerate(self._multi_config.jiras):
            container.mount(Horizontal(
                Button(jcfg.name, id=f"edit-{idx}", classes="jira-name-btn"),
                Button("Delete", id=f"del-{idx}", classes="jira-del-btn"),
                classes="jira-row",
            ))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "close-btn":
            self.dismiss(None)
        elif btn_id == "add-btn":
            self.app.push_screen(
                JiraEditScreen(self._multi_config),
                lambda _: self._rebuild_list(),
            )
        elif btn_id.startswith("edit-"):
            idx = int(btn_id[5:])
            self.app.push_screen(
                JiraEditScreen(self._multi_config, self._multi_config.jiras[idx]),
                lambda _: self._rebuild_list(),
            )
        elif btn_id.startswith("del-"):
            idx = int(btn_id[4:])
            name = self._multi_config.jiras[idx].name
            self.app.push_screen(
                ConfirmModal(f"Delete  {name}?"),
                lambda confirmed, i=idx: self._do_delete(confirmed, i),
            )

    def _do_delete(self, confirmed: bool | None, idx: int) -> None:
        if confirmed:
            self._multi_config.remove(idx)
            self._multi_config.save()
            self._rebuild_list()


class JiraEditScreen(Screen):
    """Credentials form for adding or editing a single Jira instance."""

    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def action_dismiss(self) -> None:
        self.dismiss(None)

    CSS = """
    JiraEditScreen { align: center middle; }
    #edit-box {
        width: 70; height: auto;
        border: round $accent; padding: 1 2; background: $surface;
    }
    #edit-title {
        text-align: center; text-style: bold; color: $accent; margin-bottom: 1;
    }
    .field-label { margin-top: 1; color: $text-muted; }
    #error-msg { color: $error; text-align: center; height: 1; }
    #success-msg { color: $success; text-align: center; height: 1; }
    #btn-row { margin-top: 1; align: center middle; height: 3; width: 100%; }
    """

    def __init__(self, multi_config: MultiConfig, jira_config: JiraConfig | None = None,
                 **kwargs):
        super().__init__(**kwargs)
        self._multi_config = multi_config
        self._existing = jira_config  # None means new entry

    def compose(self) -> ComposeResult:
        cfg = self._existing or JiraConfig()
        title = f"Edit  {cfg.name}" if self._existing else "Add Jira Instance"
        with Container(id="edit-box"):
            yield Static(f"⚙  {title}", id="edit-title")

            yield Label("Auth type", classes="field-label")
            yield Select(
                [("Cloud (Atlassian Cloud + API token)", "cloud"),
                 ("Server / Data Center (PAT)", "server")],
                value=cfg.auth_type or "cloud",
                id="auth-type",
            )

            yield Label("Jira URL  (e.g. https://yourcompany.atlassian.net)",
                        classes="field-label")
            yield Input(value=cfg.jira_url, id="url-input", placeholder="https://...")

            yield Label("Email / username", classes="field-label")
            yield Input(value=cfg.email, id="email-input", placeholder="you@example.com")

            yield Label("API token / Personal Access Token", classes="field-label")
            yield Input(value=cfg.api_token, id="token-input",
                        placeholder="paste token here", password=True)

            yield Static("", id="error-msg")
            yield Static("", id="success-msg")

            with Horizontal(id="btn-row"):
                yield Button("Test & Save", variant="primary", id="save-btn")
                yield Button("Cancel [Esc]", variant="error", id="cancel-btn")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "url-input":
            if "atlassian.net" in event.value:
                self.query_one("#auth-type", Select).value = "cloud"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "save-btn":
            self._save()

    def on_input_submitted(self, _) -> None:
        self._save()

    def _save(self) -> None:
        self.query_one("#error-msg", Static).update("")
        self.query_one("#success-msg", Static).update("")

        url = self.query_one("#url-input", Input).value.strip().rstrip("/")
        email = self.query_one("#email-input", Input).value.strip()
        token = self.query_one("#token-input", Input).value.strip()
        auth_type = str(self.query_one("#auth-type", Select).value)

        if not url:
            self.query_one("#error-msg", Static).update("Jira URL is required")
            return
        if not token:
            self.query_one("#error-msg", Static).update("API token is required")
            return
        if auth_type == "cloud" and not email:
            self.query_one("#error-msg", Static).update("Email is required for Cloud auth")
            return

        new_cfg = JiraConfig(jira_url=url, email=email, api_token=token, auth_type=auth_type)
        client = JiraClient(new_cfg)
        try:
            name = client.test_connection()
            self._multi_config.add_or_update(new_cfg)
            self._multi_config.save()
            self.app.notify(f"Connected as {name}", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.query_one("#error-msg", Static).update(f"Connection failed: {e}")


class ConfirmModal(Screen):
    """Simple yes/no confirmation dialog."""

    BINDINGS = [Binding("escape", "dismiss_no", "No")]

    CSS = """
    ConfirmModal { align: center middle; }
    #confirm-box {
        width: 50; height: auto;
        border: round $warning; padding: 1 2; background: $surface;
    }
    #confirm-text { text-align: center; margin-bottom: 1; }
    #btn-row { height: 3; align: center middle; }
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self._message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-box"):
            yield Static(self._message, id="confirm-text")
            with Horizontal(id="btn-row"):
                yield Button("Yes, delete", variant="error", id="yes-btn")
                yield Button("Cancel [Esc]", variant="primary", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes-btn")

    def action_dismiss_no(self) -> None:
        self.dismiss(False)


# Keep old name as alias so any remaining import doesn't break
SetupScreen = JiraListScreen
