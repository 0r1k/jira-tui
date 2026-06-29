from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from ..config import Config
from ..client import JiraClient


class SetupScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Cancel")]

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #setup-box {
        width: 70;
        height: auto;
        border: round $accent;
        padding: 1 2;
        background: $surface;
    }
    #setup-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    .field-label {
        margin-top: 1;
        color: $text-muted;
    }
    #error-msg {
        color: $error;
        text-align: center;
        height: 1;
    }
    #success-msg {
        color: $success;
        text-align: center;
        height: 1;
    }
    #btn-row {
        margin-top: 1;
        align: center middle;
        height: 3;
        width: 100%;
    }
    """

    def __init__(self, config: Config, **kwargs):
        super().__init__(**kwargs)
        self._config = config

    def compose(self) -> ComposeResult:
        with Container(id="setup-box"):
            yield Static("⚙  Jira TUI — Setup", id="setup-title")

            yield Label("Auth type", classes="field-label")
            yield Select(
                [("Cloud (Atlassian Cloud + API token)", "cloud"),
                 ("Server / Data Center (PAT)", "server")],
                value=self._config.auth_type or "cloud",
                id="auth-type",
            )

            yield Label("Jira URL  (e.g. https://yourcompany.atlassian.net)", classes="field-label")
            yield Input(value=self._config.jira_url, id="url-input", placeholder="https://...")

            yield Label("Email / username", classes="field-label")
            yield Input(value=self._config.email, id="email-input", placeholder="you@example.com")

            yield Label("API token / Personal Access Token", classes="field-label")
            yield Input(value=self._config.api_token, id="token-input",
                        placeholder="paste token here", password=True)

            yield Static("", id="error-msg")
            yield Static("", id="success-msg")

            with Horizontal(id="btn-row"):
                yield Button("Test & Save", variant="primary", id="save-btn")
                yield Button("Cancel [Esc]", variant="error", id="cancel-btn")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "url-input":
            url = event.value.strip()
            if "atlassian.net" in url:
                self.query_one("#auth-type", Select).value = "cloud"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "save-btn":
            self._save()

    def on_input_submitted(self, event: Input.Submitted) -> None:
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

        self._config.jira_url = url
        self._config.email = email
        self._config.api_token = token
        self._config.auth_type = auth_type

        client = JiraClient(self._config)
        try:
            name = client.test_connection()
            self._config.save()
            self.query_one("#success-msg", Static).update(f"Connected as {name} ✓")
            self.app.notify(f"Connected as {name}", severity="information")
            self.app.pop_screen()
        except Exception as e:
            self.query_one("#error-msg", Static).update(f"Connection failed: {e}")
