# Copyright (c) 2026 or1k.net
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static, Tree
from textual.widgets.tree import TreeNode
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding
from textual import work
from ..client import JiraClient
from ..config import Config

PRIORITY_ICONS = {"Highest": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Lowest": "⚪"}


class MainScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("n", "new_issue", "New Issue", show=True),
        Binding("f", "search", "Search", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("s", "setup", "Settings", show=True),
        Binding("enter", "open_issue", "Open Issue", show=True),
        Binding("?", "help", "Help", show=True),
    ]

    CSS = """
    MainScreen { background: $background; }

    #app-header {
        height: 3;
        background: $accent;
        color: $background;
        padding: 0 2;
        content-align: left middle;
        text-style: bold;
    }

    #main-body {
        height: 1fr;
    }

    #sidebar {
        width: 24;
        border-right: solid $panel;
        background: $surface;
    }

    #sidebar-title {
        background: $panel;
        padding: 0 1;
        text-style: bold;
        color: $accent;
        height: 3;
        content-align: left middle;
    }

    #nav-tree {
        height: 1fr;
        padding: 0;
    }

    #content-panel {
        width: 1fr;
    }

    #content-header {
        height: 3;
        background: $surface;
        border-bottom: solid $panel;
        padding: 0 2;
        content-align: left middle;
        color: $text-muted;
        text-style: bold;
    }

    #issues-table {
        height: 1fr;
    }

    #quick-search-row {
        height: 3;
        background: $surface-darken-1;
        border-bottom: solid $panel;
        padding: 0 2;
        display: none;
    }

    #quick-search-row.visible {
        display: block;
    }
    """

    def __init__(self, client: JiraClient, config: Config, **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._config = config
        self._projects: list[dict] = []
        self._current_view = "my_issues"
        self._current_label = "My Issues"

    def compose(self) -> ComposeResult:
        yield Static("⚡ Jira TUI © or1k.net", id="app-header")
        with Horizontal(id="main-body"):
            with Vertical(id="sidebar"):
                yield Static("Navigation", id="sidebar-title")
                yield Tree("", id="nav-tree")
            with Vertical(id="content-panel"):
                yield Static("My Issues", id="content-header")
                yield Horizontal(
                    Input(placeholder="Quick filter (title substring)…", id="quick-filter"),
                    id="quick-search-row",
                )
                yield DataTable(id="issues-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#issues-table", DataTable)
        table.add_columns("Key", "Type", "Summary", "Status", "Priority", "Assignee", "Updated")
        self._build_nav()
        self._load_my_issues()

    # ── Nav tree ─────────────────────────────────────────────────────────────

    def _build_nav(self) -> None:
        tree = self.query_one("#nav-tree", Tree)
        tree.clear()
        root = tree.root
        root.expand()

        me_node = root.add("👤 My Issues", data={"type": "my_issues"})
        root.add("📋 Reported by me", data={"type": "reported_by_me"})
        root.add("👀 Watching", data={"type": "watching"})
        root.add("🔍 Search (JQL)", data={"type": "jql_search"})

        projects_node = root.add("📁 Projects", data={"type": "header"})
        self._load_projects_into_tree(projects_node)

    @work(thread=True)
    def _load_projects_into_tree(self, node: TreeNode) -> None:
        try:
            projects = self._client.get_projects()
            self.app.call_from_thread(self._add_projects_to_tree, node, projects)
        except Exception:
            pass

    def _add_projects_to_tree(self, node: TreeNode, projects: list[dict]) -> None:
        self._projects = projects
        for p in projects[:30]:  # cap at 30 to avoid huge trees
            node.add_leaf(f"{p['key']}  {p['name']}", data={"type": "project", "key": p["key"]})
        node.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if not data:
            return
        t = data.get("type")
        if t == "my_issues":
            self._current_view = "my_issues"
            self._current_label = "My Issues"
            self._load_my_issues()
        elif t == "reported_by_me":
            self._current_view = "reported_by_me"
            self._current_label = "Reported by Me"
            self._load_issues("reporter = currentUser() ORDER BY updated DESC")
        elif t == "watching":
            self._current_view = "watching"
            self._current_label = "Watching"
            self._load_issues("watcher = currentUser() ORDER BY updated DESC")
        elif t == "jql_search":
            self.action_search()
        elif t == "project":
            key = data["key"]
            self._current_view = f"project:{key}"
            self._current_label = f"Project: {key}"
            self._load_issues(f"project = {key} ORDER BY updated DESC")

    # ── Issue loading ─────────────────────────────────────────────────────────

    def _load_my_issues(self) -> None:
        self._load_issues("assignee = currentUser() ORDER BY updated DESC")

    def _load_issues(self, jql: str) -> None:
        self.query_one("#content-header", Static).update(f"{self._current_label}  [dim]loading…[/]")
        table = self.query_one("#issues-table", DataTable)
        table.clear()
        self._fetch_issues(jql)

    @work(thread=True)
    def _fetch_issues(self, jql: str) -> None:
        try:
            issues = self._client.search_issues(jql, max_results=100)
            self.app.call_from_thread(self._populate_table, issues)
        except Exception as e:
            self.app.call_from_thread(
                self.query_one("#content-header", Static).update,
                f"{self._current_label}  [red]Error: {e}[/]",
            )

    def _populate_table(self, issues) -> None:
        table = self.query_one("#issues-table", DataTable)
        table.clear()
        for issue in issues:
            f = issue.fields
            priority = getattr(f.priority, "name", "?") if f.priority else "?"
            icon = PRIORITY_ICONS.get(priority, "•")
            assignee = getattr(f.assignee, "displayName", "—") if f.assignee else "—"
            updated = str(getattr(f, "updated", ""))[:10]
            status = getattr(f.status, "name", "?")
            itype = getattr(f.issuetype, "name", "?") if f.issuetype else "?"
            table.add_row(
                issue.key,
                itype,
                (f.summary or "")[:55],
                status,
                f"{icon} {priority}",
                assignee,
                updated,
                key=issue.key,
            )
        count = len(issues)
        self.query_one("#content-header", Static).update(
            f"{self._current_label}  [dim]({count} issues)[/]"
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_open_issue(self) -> None:
        table = self.query_one("#issues-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key = table.get_row_at(table.cursor_row)
            issue_key = str(row_key[0])
            from .issue_detail import IssueDetailScreen
            self.app.push_screen(IssueDetailScreen(self._client, issue_key))
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        issue_key = str(event.row_key.value)
        from .issue_detail import IssueDetailScreen
        self.app.push_screen(IssueDetailScreen(self._client, issue_key))

    def action_new_issue(self) -> None:
        from .create_issue import CreateIssueScreen
        self.app.push_screen(
            CreateIssueScreen(self._client, self._projects),
            self._on_issue_created,
        )

    def _on_issue_created(self, issue_key) -> None:
        if issue_key:
            from .issue_detail import IssueDetailScreen
            self.app.push_screen(IssueDetailScreen(self._client, issue_key))

    def action_search(self) -> None:
        from .search_screen import SearchScreen
        self.app.push_screen(SearchScreen(self._client))

    def action_refresh(self) -> None:
        if self._current_view == "my_issues":
            self._load_my_issues()
        elif self._current_view == "reported_by_me":
            self._load_issues("reporter = currentUser() ORDER BY updated DESC")
        elif self._current_view == "watching":
            self._load_issues("watcher = currentUser() ORDER BY updated DESC")
        elif self._current_view.startswith("project:"):
            key = self._current_view.split(":", 1)[1]
            self._load_issues(f"project = {key} ORDER BY updated DESC")

    def action_setup(self) -> None:
        from .setup import SetupScreen
        self.app.push_screen(SetupScreen(self._config))

    def action_quit(self) -> None:
        self.app.exit()

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())


class HelpScreen(Screen):
    BINDINGS = [Binding("escape,q,?", "app.pop_screen", "Close")]

    CSS = """
    HelpScreen { align: center middle; }
    #help-box {
        width: 60; height: auto; border: round $accent;
        padding: 1 2; background: $surface;
    }
    .help-title { text-align: center; text-style: bold; color: $accent; margin-bottom: 1; }
    .help-row { margin-bottom: 0; }
    .key { color: $accent; text-style: bold; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="help-box"):
            yield Static("Keyboard Shortcuts", classes="help-title")
            bindings = [
                ("n", "New issue"),
                ("f", "Search / JQL"),
                ("r", "Refresh current view"),
                ("s", "Settings / auth"),
                ("Enter", "Open selected issue"),
                ("q", "Quit"),
                ("?", "This help"),
                ("", ""),
                ("Issue detail", ""),
                ("t", "Transition status"),
                ("c", "Add comment"),
                ("e", "Edit summary"),
                ("r", "Refresh issue"),
                ("Esc", "Go back"),
                ("", ""),
                ("Comment modal", ""),
                ("Ctrl+S", "Submit comment"),
                ("Esc", "Cancel"),
            ]
            for key, desc in bindings:
                if not key and not desc:
                    yield Static("")
                elif not desc:
                    yield Static(f"[bold]{key}[/]", classes="help-row")
                else:
                    yield Static(f"[bold cyan]{key:12}[/] {desc}", classes="help-row")
            yield Static("")
            yield Button("Close [Esc]", variant="primary", id="close-btn")

    def on_button_pressed(self, _) -> None:
        self.app.pop_screen()
