# Copyright (c) 2026 or1k.net
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Collapsible, DataTable, Input, Label, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual import work
from ..client import JiraClient

PRIORITY_ICONS = {"Highest": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Lowest": "⚪"}

QUICK_FILTERS = [
    ("My open",        "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"),
    ("My in progress", "assignee = currentUser() AND status = \"In Progress\" ORDER BY updated DESC"),
    ("Reported by me", "reporter = currentUser() ORDER BY created DESC"),
    ("High priority",  "priority in (High, Highest) AND statusCategory != Done ORDER BY priority ASC"),
    ("Updated today",  "updated >= startOfDay() ORDER BY updated DESC"),
    ("Unresolved bugs","issuetype = Bug AND resolution = Unresolved ORDER BY priority ASC"),
]

JQL_TIPS = """\
[bold]Operators[/]
  =  !=  ~  !~  >  <  >=  <=
  IN (...)    NOT IN (...)
  IS EMPTY    IS NOT EMPTY

[bold]Fields[/]
  project, issuetype, status, priority
  assignee, reporter, creator
  summary, description, comment
  created, updated, duedate
  sprint, fixVersion, labels

[bold]Functions[/]
  currentUser()
  startOfDay()  endOfDay()
  startOfWeek() startOfMonth()
  openSprints() closedSprints()

[bold]Examples[/]
  project = ITSD AND status = "In Progress"
  assignee = currentUser() AND sprint in openSprints()
  text ~ "deploy" AND updated >= -7d
  priority = High AND assignee is EMPTY
  labels = backend AND statusCategory != Done
"""


class SearchScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+f", "focus_input", "Focus search", show=False),
    ]

    CSS = """
    SearchScreen { background: $background; }

    #search-header {
        height: auto;
        background: $surface;
        border-bottom: solid $accent;
        padding: 1 2;
    }

    #jql-row { height: 3; margin-bottom: 1; }

    #jql-input { width: 1fr; }

    #quick-row {
        height: 3;
        margin-bottom: 1;
    }

    .quick-btn {
        margin-right: 1;
        margin-bottom: 1;
        height: 3;
        min-width: 14;
        background: $panel;
        border: tall $panel;
        color: $text;
    }

    .quick-btn:hover { background: $accent; color: $background; }

    #tips-collapsible { margin-top: 0; }

    #jql-tips {
        padding: 0 2;
        color: $text-muted;
    }

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
            with Horizontal(id="jql-row"):
                yield Input(
                    value=self._initial_jql,
                    placeholder="assignee = currentUser() AND status = \"In Progress\"",
                    id="jql-input",
                )
                yield Button("Search", variant="primary", id="search-btn")
                yield Button("Back [Esc]", variant="error", id="back-btn")

            yield Label("Quick filters:", classes="search-label")
            with Horizontal(id="quick-row"):
                for label, jql in QUICK_FILTERS:
                    yield Button(label, classes="quick-btn", id=f"qf-{label.replace(' ', '_')}")

            with Collapsible(title="JQL syntax reference", collapsed=True, id="tips-collapsible"):
                yield Static(JQL_TIPS, id="jql-tips")

        yield DataTable(id="results-table", cursor_type="row", zebra_stripes=True)
        yield Static("Type JQL and press Enter  |  click row or Enter to open  |  Esc — back", id="status-bar")

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Key", "Summary", "Status", "Priority", "Assignee", "Updated")
        # Focus the input so the user can type immediately
        self.query_one("#jql-input", Input).focus()
        if self._initial_jql:
            self._run_search(self._initial_jql)

    def action_focus_input(self) -> None:
        self.query_one("#jql-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "back-btn":
            self.app.pop_screen()
            return
        if btn_id == "search-btn":
            self._search_from_input()
            return
        # Quick filter buttons
        if btn_id.startswith("qf-"):
            label = btn_id[3:].replace("_", " ")
            jql = next((q for l, q in QUICK_FILTERS if l == label), None)
            if jql:
                self.query_one("#jql-input", Input).value = jql
                self._run_search(jql)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "jql-input":
            self._search_from_input()

    def _search_from_input(self) -> None:
        jql = self.query_one("#jql-input", Input).value.strip()
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
            err = str(e).splitlines()[0]
            self.app.call_from_thread(
                self.query_one("#status-bar", Static).update, f"Error: {err}"
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
            f"{count} result(s)  |  Enter or click — open issue  |  Esc — back"
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        issue_key = str(event.row_key.value)
        from .issue_detail import IssueDetailScreen
        self.app.push_screen(IssueDetailScreen(self._client, issue_key))
