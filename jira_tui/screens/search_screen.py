# Copyright (c) 2026 or1k.net
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Label, Static
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from textual import work
from ..client import JiraClient

PRIORITY_ICONS = {"Highest": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Lowest": "⚪"}


class SearchScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "open_issue", "Open"),
    ]

    CSS = """
    SearchScreen { background: $background; }
    #search-header {
        height: 5;
        background: $surface;
        border-bottom: solid $accent;
        padding: 1 2;
    }
    .search-label { color: $text-muted; margin-bottom: 0; }
    #jql-row { height: 3; }
    #results-table { height: 1fr; }
    #status-bar {
        height: 1;
        background: $surface-darken-1;
        padding: 0 2;
        color: $text-muted;
    }
    """

    def __init__(self, client: JiraClient, initial_jql: str = "", **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._initial_jql = initial_jql

    def compose(self) -> ComposeResult:
        with Vertical(id="search-header"):
            yield Label("JQL Search", classes="search-label")
            with Horizontal(id="jql-row"):
                yield Input(
                    value=self._initial_jql,
                    placeholder='e.g.  project = MYPROJ AND status = "In Progress"',
                    id="jql-input",
                )
                yield Button("Search", variant="primary", id="search-btn")
                yield Button("Back [Esc]", variant="error", id="back-btn")
        yield DataTable(id="results-table", cursor_type="row", zebra_stripes=True)
        yield Static("Enter — open issue  |  Esc — back", id="status-bar")

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Key", "Summary", "Status", "Priority", "Assignee", "Updated")
        if self._initial_jql:
            self._run_search(self._initial_jql)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "search-btn":
            jql = self.query_one("#jql-input", Input).value.strip()
            if jql:
                self._run_search(jql)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "jql-input":
            jql = event.input.value.strip()
            if jql:
                self._run_search(jql)

    @work(thread=True)
    def _run_search(self, jql: str) -> None:
        self.app.call_from_thread(
            self.query_one("#status-bar", Static).update, "Searching…"
        )
        try:
            issues = self._client.search_issues(jql, max_results=100)
            self.app.call_from_thread(self._populate, issues)
        except Exception as e:
            self.app.call_from_thread(
                self.query_one("#status-bar", Static).update, f"Error: {e}"
            )

    def _populate(self, issues) -> None:
        table = self.query_one("#results-table", DataTable)
        table.clear()
        for issue in issues:
            f = issue.fields
            priority = getattr(f.priority, "name", "?") if f.priority else "?"
            icon = PRIORITY_ICONS.get(priority, "•")
            assignee = getattr(f.assignee, "displayName", "—") if f.assignee else "—"
            updated = str(getattr(f, "updated", ""))[:10]
            status = getattr(f.status, "name", "?")
            table.add_row(
                issue.key,
                (f.summary or "")[:60],
                status,
                f"{icon} {priority}",
                assignee,
                updated,
                key=issue.key,
            )
        count = len(issues)
        self.query_one("#status-bar", Static).update(
            f"{count} result(s) | Enter to open | Esc to back"
        )

    def action_open_issue(self) -> None:
        table = self.query_one("#results-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            issue_key = str(row_key[0])
            from .issue_detail import IssueDetailScreen
            self.app.push_screen(IssueDetailScreen(self._client, issue_key))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        issue_key = str(event.row_key.value)
        from .issue_detail import IssueDetailScreen
        self.app.push_screen(IssueDetailScreen(self._client, issue_key))
