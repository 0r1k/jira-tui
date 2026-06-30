# Copyright (c) 2026 or1k.net
from textual.app import App
from textual.binding import Binding
from textual.widgets import Input, TextArea
from .config import Config
from .client import JiraClient


class JiraTuiApp(App):
    TITLE = "Jira TUI"
    CSS = ""
    BINDINGS = [
        Binding("ctrl+a", "select_all_focused", show=False, priority=True),
    ]

    def action_select_all_focused(self) -> None:
        focused = self.focused
        if isinstance(focused, (Input, TextArea)):
            focused.action_select_all()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._config = Config()
        self._client: JiraClient | None = None

    def on_mount(self) -> None:
        configured = self._config.load()
        if not configured:
            from .screens.setup import SetupScreen
            self.push_screen(SetupScreen(self._config), self._after_setup)
        else:
            self._launch_main()

    def _after_setup(self, _) -> None:
        if self._config.is_configured():
            self._launch_main()
        else:
            self.exit()

    def _launch_main(self) -> None:
        self._client = JiraClient(self._config)
        from .screens.main_screen import MainScreen
        self.push_screen(MainScreen(self._client, self._config))
