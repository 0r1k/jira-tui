# Copyright (c) 2026 or1k.net
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static, Tree
from textual.widgets.tree import TreeNode
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding
from textual import events, work
from ..client import JiraClient
from ..config import JiraConfig, MultiConfig


class ResizeHandle(Static):
    """1-cell drag handle that resizes the sidebar."""

    DEFAULT_CSS = """
    ResizeHandle {
        width: 1;
        background: $panel;
        color: $text-muted;
    }
    ResizeHandle:hover { background: $accent; color: $background; }
    """

    def __init__(self) -> None:
        super().__init__("▌")
        self._dragging = False
        self._width = 0

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self._dragging = True
        self._width = self.screen.query_one("#sidebar").size.width
        self.capture_mouse()
        event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if not self._dragging:
            return
        self._width = max(15, min(70, self._width + event.delta_x))
        self.screen.query_one("#sidebar").styles.width = self._width
        event.stop()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._dragging:
            self._dragging = False
            self.release_mouse()
        event.stop()

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
        width: 31;
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

    def __init__(self, clients: list[tuple[JiraClient, JiraConfig]],
                 multi_config: MultiConfig, **kwargs):
        super().__init__(**kwargs)
        self._clients = clients
        self._multi_config = multi_config
        self._projects_per_client: dict[int, list[dict]] = {}
        self._current_client_idx: int = 0
        self._current_view: str = "0:my_issues"
        self._current_label: str = "My Issues"

    def compose(self) -> ComposeResult:
        yield Static("⚡ Jira TUI © or1k.net", id="app-header")
        with Horizontal(id="main-body"):
            with Vertical(id="sidebar"):
                yield Static("Navigation", id="sidebar-title")
                yield Tree("", id="nav-tree")
            yield ResizeHandle()
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
        if self._clients:
            self._load_issues(0, "assignee = currentUser() ORDER BY updated DESC")

    # ── Nav tree ─────────────────────────────────────────────────────────────

    def _build_nav(self) -> None:
        tree = self.query_one("#nav-tree", Tree)
        tree.clear()
        root = tree.root
        root.expand()

        for idx, (client, jcfg) in enumerate(self._clients):
            domain = jcfg.name
            jira_node = root.add(
                f"● {domain}", data={"type": "jira_root", "client_idx": idx}
            )
            jira_node.add_leaf(
                "👤 My Issues", data={"type": "my_issues", "client_idx": idx}
            )
            jira_node.add_leaf(
                "📋 Reported by me", data={"type": "reported_by_me", "client_idx": idx}
            )
            jira_node.add_leaf(
                "👀 Watching", data={"type": "watching", "client_idx": idx}
            )
            jira_node.add_leaf(
                "🔍 Search (JQL)", data={"type": "jql_search", "client_idx": idx}
            )
            projects_node = jira_node.add(
                "📁 Projects", data={"type": "projects_header", "client_idx": idx}
            )
            self._load_projects_into_tree(idx, projects_node)
            jira_node.expand()

    @work(thread=True)
    def _load_projects_into_tree(self, client_idx: int, node: TreeNode) -> None:
        try:
            client = self._clients[client_idx][0]
            projects = client.get_projects()
            self.app.call_from_thread(self._add_projects_to_tree, client_idx, node, projects)
        except Exception:
            pass

    def _add_projects_to_tree(self, client_idx: int, node: TreeNode,
                               projects: list[dict]) -> None:
        self._projects_per_client[client_idx] = projects
        for p in projects[:30]:
            node.add_leaf(
                f"{p['key']}  {p['name']}",
                data={"type": "project", "client_idx": client_idx, "key": p["key"]},
            )
        node.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if not data:
            return
        t = data.get("type")
        if t in ("jira_root", "projects_header"):
            return

        client_idx: int = data.get("client_idx", 0)
        self._current_client_idx = client_idx

        if t == "my_issues":
            self._current_view = f"{client_idx}:my_issues"
            self._current_label = "My Issues"
            self._load_issues(client_idx, "assignee = currentUser() ORDER BY updated DESC")
        elif t == "reported_by_me":
            self._current_view = f"{client_idx}:reported_by_me"
            self._current_label = "Reported by Me"
            self._load_issues(client_idx, "reporter = currentUser() ORDER BY updated DESC")
        elif t == "watching":
            self._current_view = f"{client_idx}:watching"
            self._current_label = "Watching"
            self._load_issues(client_idx, "watcher = currentUser() ORDER BY updated DESC")
        elif t == "jql_search":
            self.action_search()
        elif t == "project":
            key = data["key"]
            self._current_view = f"{client_idx}:project:{key}"
            self._current_label = f"Project: {key}"
            self._load_issues(client_idx, f"project = {key} ORDER BY updated DESC")

    # ── Issue loading ─────────────────────────────────────────────────────────

    def _load_issues(self, client_idx: int, jql: str) -> None:
        self.query_one("#content-header", Static).update(
            f"{self._current_label}  [dim]loading…[/]"
        )
        table = self.query_one("#issues-table", DataTable)
        table.clear()
        self._fetch_issues(client_idx, jql)

    @work(thread=True)
    def _fetch_issues(self, client_idx: int, jql: str) -> None:
        try:
            client = self._clients[client_idx][0]
            issues = client.search_issues(jql, max_results=100)
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

    def _current_client(self) -> JiraClient:
        return self._clients[self._current_client_idx][0]

    def action_open_issue(self) -> None:
        table = self.query_one("#issues-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key = table.get_row_at(table.cursor_row)
            issue_key = str(row_key[0])
            from .issue_detail import IssueDetailScreen
            self.app.push_screen(IssueDetailScreen(self._current_client(), issue_key))
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        issue_key = str(event.row_key.value)
        from .issue_detail import IssueDetailScreen
        self.app.push_screen(IssueDetailScreen(self._current_client(), issue_key))

    def action_new_issue(self) -> None:
        if not self._clients:
            self.app.notify("No Jira instances configured", severity="warning")
            return
        projects = self._projects_per_client.get(self._current_client_idx, [])
        from .create_issue import CreateIssueScreen
        self.app.push_screen(
            CreateIssueScreen(self._current_client(), projects),
            self._on_issue_created,
        )

    def _on_issue_created(self, issue_key) -> None:
        if issue_key:
            from .issue_detail import IssueDetailScreen
            self.app.push_screen(IssueDetailScreen(self._current_client(), issue_key))

    def action_search(self) -> None:
        if not self._clients:
            return
        from .search_screen import SearchScreen
        self.app.push_screen(SearchScreen(self._current_client()))

    def action_refresh(self) -> None:
        view = self._current_view
        parts = view.split(":", 2)
        if len(parts) < 2:
            return
        try:
            client_idx = int(parts[0])
        except ValueError:
            return
        view_type = parts[1]
        if view_type == "my_issues":
            self._load_issues(client_idx, "assignee = currentUser() ORDER BY updated DESC")
        elif view_type == "reported_by_me":
            self._load_issues(client_idx, "reporter = currentUser() ORDER BY updated DESC")
        elif view_type == "watching":
            self._load_issues(client_idx, "watcher = currentUser() ORDER BY updated DESC")
        elif view_type == "project" and len(parts) == 3:
            key = parts[2]
            self._load_issues(client_idx, f"project = {key} ORDER BY updated DESC")

    def action_setup(self) -> None:
        from .setup import JiraListScreen
        self.app.push_screen(JiraListScreen(self._multi_config), self._on_setup_done)

    def _on_setup_done(self, _) -> None:
        self._clients = [
            (JiraClient(jcfg), jcfg)
            for jcfg in self._multi_config.jiras
            if jcfg.is_configured()
        ]
        self._projects_per_client = {}
        self._build_nav()
        if self._clients:
            self._current_client_idx = 0
            self._current_view = "0:my_issues"
            self._current_label = "My Issues"
            self._load_issues(0, "assignee = currentUser() ORDER BY updated DESC")

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
                ("s", "Settings / connections"),
                ("Enter", "Open selected issue"),
                ("q", "Quit"),
                ("?", "This help"),
                ("", ""),
                ("Issue detail", ""),
                ("t", "Transition status"),
                ("c", "Add comment"),
                ("a", "Assign"),
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
