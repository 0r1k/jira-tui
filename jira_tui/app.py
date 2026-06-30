# Copyright (c) 2026 or1k.net
from textual.app import App
from textual.binding import Binding
from textual.widgets import Input, TextArea
from .config import MultiConfig, JiraConfig
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
        self._multi_config = MultiConfig()

    def on_mount(self) -> None:
        configured = self._multi_config.load()
        if not configured:
            from .screens.setup import JiraListScreen
            self.push_screen(JiraListScreen(self._multi_config), self._after_setup)
        else:
            self._launch_main()

    def _after_setup(self, _) -> None:
        if self._multi_config.is_configured():
            self._launch_main()
        else:
            self.exit()

    def _launch_main(self) -> None:
        clients = [
            (JiraClient(jcfg), jcfg)
            for jcfg in self._multi_config.jiras
            if jcfg.is_configured()
        ]
        from .screens.main_screen import MainScreen
        self.push_screen(MainScreen(clients, self._multi_config))
