# Copyright (c) 2026 or1k.net
from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Markdown, Select, Static, TextArea
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.binding import Binding
from textual import work
from ..client import JiraClient




PRIORITY_ICONS = {"Highest": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵", "Lowest": "⚪"}
STATUS_COLORS = {"To Do": "blue", "In Progress": "yellow", "Done": "green", "Closed": "green"}


class CommentBox(Vertical):
    """Single comment rendered as a self-contained widget with compose()."""

    DEFAULT_CSS = """
    CommentBox {
        background: $surface;
        border: solid $panel;
        margin-bottom: 0;
        padding: 0 1;
        height: auto;
    }
    """

    def __init__(self, author: str, date: str, body: str):
        super().__init__()
        self._author = author
        self._date = date
        self._body = body

    def compose(self) -> ComposeResult:
        yield Static(f"[bold cyan]{self._author}[/] [dim]{self._date}[/]  {self._body or '(empty)'}")


class IssueDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", show=True),
        Binding("t", "transition", "Transition", show=True),
        Binding("c", "comment", "Comment", show=True),
        Binding("a", "assign", "Assign", show=True),
        Binding("e", "edit_summary", "Edit Summary", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    CSS = """
    IssueDetailScreen {
        background: $background;
    }
    #detail-header {
        height: 3;
        background: $surface;
        border-bottom: solid $accent;
        padding: 0 2;
        content-align: left middle;
    }
    #detail-key {
        color: $accent;
        text-style: bold;
        margin-right: 2;
    }
    #detail-summary {
        text-style: bold;
    }
    #meta-bar {
        height: 3;
        background: $surface-darken-1;
        padding: 0 2;
        border-bottom: solid $panel;
        content-align: left middle;
    }
    #body-container {
        height: 1fr;
    }
    #description-panel {
        width: 2fr;
        border-right: solid $panel;
        padding: 1 2;
    }
    #right-panel {
        width: 1fr;
        padding: 1 2;
    }
    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        border-bottom: solid $panel;
    }
    .comment-box {
        background: $surface;
        border: round $panel;
        margin-bottom: 1;
        padding: 1;
    }
    .comment-author {
        text-style: bold;
        color: $accent;
    }
    .comment-date {
        color: $text-muted;
    }
    """

    def __init__(self, client: JiraClient, issue_key: str, **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._issue_key = issue_key
        self._issue = None

    def compose(self) -> ComposeResult:
        yield Static(f"Loading {self._issue_key}…", id="detail-header")
        yield Static("", id="meta-bar")
        with Horizontal(id="body-container"):
            with ScrollableContainer(id="description-panel"):
                yield Static("Description", classes="section-title")
                yield Markdown("", id="description-md")
            with ScrollableContainer(id="right-panel"):
                yield Static("Comments", classes="section-title")
                yield Vertical(id="comments-list")
        yield Footer()

    def on_mount(self) -> None:
        self._load_issue()

    @work(thread=True)
    def _load_issue(self) -> None:
        try:
            issue = self._client.get_issue(self._issue_key)
            comments = self._client.get_comments(self._issue_key)
            self.app.call_from_thread(self._populate, issue, comments)
        except Exception as e:
            self.app.call_from_thread(
                self.query_one("#detail-header", Static).update,
                f"Error loading {self._issue_key}: {e}"
            )

    def _populate(self, issue, comments) -> None:
        self._issue = issue
        f = issue.fields

        key = issue.key
        summary = f.summary or ""
        status = getattr(f.status, "name", "?")
        priority = getattr(f.priority, "name", "?") if f.priority else "?"
        assignee = getattr(f.assignee, "displayName", "Unassigned") if f.assignee else "Unassigned"
        reporter = getattr(f.reporter, "displayName", "?") if f.reporter else "?"
        itype = getattr(f.issuetype, "name", "?") if f.issuetype else "?"

        icon = PRIORITY_ICONS.get(priority, "•")

        self.query_one("#detail-header", Static).update(
            f"[bold cyan]{key}[/]  [bold]{summary}[/]"
        )

        self.query_one("#meta-bar", Static).update(
            f"[bold]{itype}[/]  │  Status: [yellow]{status}[/]  │  Priority: {icon} {priority}"
            f"  │  Assignee: [cyan]{assignee}[/]  │  Reporter: {reporter}"
        )

        desc = getattr(f, "description", None)
        if not desc:
            desc = "_No description_"
        elif isinstance(desc, str):
            # Jira stores line breaks as \n; Markdown needs trailing spaces for hard breaks
            desc = desc.replace("\n", "  \n")
        self.query_one("#description-md", Markdown).update(desc)

        comments_list = self.query_one("#comments-list", Vertical)
        comments_list.remove_children()
        if not comments:
            comments_list.mount(Static("No comments yet.", classes="comment-date"))
        else:
            for c in reversed(comments):
                author = getattr(c.author, "displayName", "?")
                date = str(c.created)[:10]
                body = c.body or ""
                comments_list.mount(CommentBox(author, date, body))

    def action_transition(self) -> None:
        if not self._issue:
            return
        self.app.push_screen(TransitionModal(self._client, self._issue_key), self._on_transitioned)

    def _on_transitioned(self, _) -> None:
        self._load_issue()

    def action_comment(self) -> None:
        self.app.push_screen(CommentModal(self._client, self._issue_key), self._on_commented)

    def _on_commented(self, _) -> None:
        self._load_issue()

    def action_assign(self) -> None:
        if not self._issue:
            return
        self.app.push_screen(AssignModal(self._client, self._issue_key), self._on_assigned)

    def _on_assigned(self, _) -> None:
        self._load_issue()

    def action_edit_summary(self) -> None:
        if not self._issue:
            return
        self.app.push_screen(
            EditSummaryModal(self._client, self._issue_key, self._issue.fields.summary),
            self._on_edited,
        )

    def _on_edited(self, _) -> None:
        self._load_issue()

    def action_refresh(self) -> None:
        self._load_issue()


# ── Modal dialogs ─────────────────────────────────────────────────────────────

class TransitionModal(Screen):
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    CSS = """
    TransitionModal { align: center middle; }
    #modal-box { width: 50; height: auto; border: round $accent; padding: 1 2; background: $surface; }
    .modal-title { text-align: center; text-style: bold; color: $accent; margin-bottom: 1; }
    #cancel-row { height: 3; align: center middle; margin-top: 1; }
    .tr-btn {
        width: 1fr; height: 3; margin: 0 0 1 0;
        background: $panel; border: tall $accent; color: $text;
        text-align: center;
    }
    .tr-btn:hover { background: $accent; color: $background; }
    .tr-btn:focus { background: $accent-darken-1; color: $background; }
    """

    def __init__(self, client: JiraClient, issue_key: str, **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._issue_key = issue_key

    def compose(self) -> ComposeResult:
        with Container(id="modal-box"):
            yield Static(f"Transition  {self._issue_key}", classes="modal-title")
            yield Static("Loading transitions…", id="transitions-area")
            with Horizontal(id="cancel-row"):
                yield Button("Cancel [Esc]", variant="error", id="btn-cancel")

    def on_mount(self) -> None:
        self._load()

    @work(thread=True)
    def _load(self) -> None:
        transitions = self._client.get_transitions(self._issue_key)
        self.app.call_from_thread(self._populate, transitions)

    def _populate(self, transitions) -> None:
        area = self.query_one("#transitions-area", Static)
        area.remove()
        cancel_row = self.query_one("#cancel-row", Horizontal)
        container = self.query_one("#modal-box", Container)
        for t in transitions:
            container.mount(
                Button(t["name"], id=f"tr-{t['id']}", classes="tr-btn"),
                before=cancel_row,
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-cancel":
            self.dismiss(None)
        elif btn_id.startswith("tr-"):
            transition_id = btn_id[3:]
            try:
                self._client.transition_issue(self._issue_key, transition_id)
                self.app.notify(f"Transitioned {self._issue_key}", severity="information")
            except Exception as e:
                self.app.notify(f"Error: {e}", severity="error")
            self.dismiss(True)


class CommentModal(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Cancel"),
        Binding("ctrl+s", "submit", "Submit"),
    ]

    CSS = """
    CommentModal { align: center middle; }
    #modal-box { width: 70; height: 20; border: round $accent; padding: 1 2; background: $surface; }
    .modal-title { text-align: center; text-style: bold; color: $accent; margin-bottom: 1; }
    #comment-area { height: 10; }
    #btn-row { height: 3; align: center middle; margin-top: 1; }
    """

    def __init__(self, client: JiraClient, issue_key: str, **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._issue_key = issue_key

    def compose(self) -> ComposeResult:
        with Container(id="modal-box"):
            yield Static(f"Add Comment to {self._issue_key}", classes="modal-title")
            yield TextArea(id="comment-area")
            with Horizontal(id="btn-row"):
                yield Button("Submit [Ctrl+S]", variant="primary", id="submit-btn")
                yield Button("Cancel [Esc]", variant="error", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_submit(self) -> None:
        body = self.query_one("#comment-area", TextArea).text.strip()
        if not body:
            self.app.notify("Comment cannot be empty", severity="warning")
            return
        try:
            self._client.add_comment(self._issue_key, body)
            self.app.notify("Comment added", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")


class EditSummaryModal(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "Cancel")]

    CSS = """
    EditSummaryModal { align: center middle; }
    #modal-box { width: 70; height: auto; border: round $accent; padding: 1 2; background: $surface; }
    .modal-title { text-align: center; text-style: bold; color: $accent; margin-bottom: 1; }
    #btn-row { height: 3; align: center middle; margin-top: 1; }
    """

    def __init__(self, client: JiraClient, issue_key: str, current_summary: str, **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._issue_key = issue_key
        self._current = current_summary

    def compose(self) -> ComposeResult:
        with Container(id="modal-box"):
            yield Static(f"Edit Summary — {self._issue_key}", classes="modal-title")
            yield Input(value=self._current, id="summary-input")
            with Horizontal(id="btn-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="error", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save()
        else:
            self.dismiss(None)

    def on_input_submitted(self, _) -> None:
        self._save()

    def _save(self) -> None:
        summary = self.query_one("#summary-input", Input).value.strip()
        if not summary:
            return
        try:
            self._client.update_issue(self._issue_key, {"summary": summary})
            self.app.notify("Summary updated", severity="information")
            self.dismiss(True)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")


class AssignModal(Screen):
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    CSS = """
    AssignModal { align: center middle; }
    #assign-box {
        width: 64; height: auto; max-height: 36;
        border: round $accent; padding: 1 2; background: $surface;
    }
    .modal-title { text-align: center; text-style: bold; color: $accent; margin-bottom: 1; }
    #user-search { width: 1fr; margin-bottom: 0; }
    #assign-status { height: 1; color: $text-muted; }
    #user-list {
        height: auto;
        max-height: 18;
        border: solid $panel;
        background: $background;
        display: none;
    }
    #user-list.visible { display: block; }
    .user-btn {
        width: 1fr; height: 3; margin: 0;
        background: $background; border: none; color: $text;
    }
    .user-btn:hover { background: $accent; color: $background; }
    .user-btn:focus { background: $accent-darken-1; color: $background; }
    #btn-row { height: 3; align: center middle; margin-top: 1; }
    """

    def __init__(self, client: JiraClient, issue_key: str, **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._issue_key = issue_key
        self._users: list[dict] = []
        self._last_query = ""
        self._me: dict | None = None

    def compose(self) -> ComposeResult:
        with Container(id="assign-box"):
            yield Static(f"Assign  {self._issue_key}", classes="modal-title")
            yield Input(placeholder="Type name to search…", id="user-search")
            yield Static("Start typing (2+ chars) to see suggestions", id="assign-status")
            yield ScrollableContainer(id="user-list")
            with Horizontal(id="btn-row"):
                yield Button("Assign to me", variant="success", id="assignme-btn")
                yield Button("Remove assignee", variant="warning", id="unassign-btn")
                yield Button("Cancel [Esc]", variant="error", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#user-search", Input).focus()
        self._load_me()

    @work(thread=True)
    def _load_me(self) -> None:
        try:
            me = self._client.get_myself()
            self.app.call_from_thread(setattr, self, "_me", me)
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "user-search":
            return
        query = event.value.strip()
        if len(query) < 2:
            self.query_one("#user-list", ScrollableContainer).remove_class("visible")
            self.query_one("#assign-status", Static).update(
                "Start typing (2+ chars) to see suggestions"
            )
            return
        if query == self._last_query:
            return
        self._last_query = query
        self.query_one("#assign-status", Static).update("Searching…")
        self._search(query)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "cancel-btn":
            self.dismiss(None)
        elif btn_id == "assignme-btn":
            if self._me:
                self._apply(self._me.get("accountId"), self._me.get("name"))
            else:
                self.app.notify("Could not load current user", severity="warning")
        elif btn_id == "unassign-btn":
            self._apply(None, None)
        elif btn_id.startswith("user-"):
            idx = int(btn_id[5:])
            user = self._users[idx]
            self._apply(user.get("accountId"), user.get("name"))

    @work(thread=True)
    def _search(self, query: str) -> None:
        try:
            users = self._client.search_users(query, issue_key=self._issue_key)
            self.app.call_from_thread(self._show_users, query, users)
        except Exception as e:
            self.app.call_from_thread(
                self.query_one("#assign-status", Static).update, f"Error: {e}"
            )

    def _show_users(self, query: str, users: list[dict]) -> None:
        # Discard stale results if the user has typed ahead
        if query != self._last_query:
            return
        self._users = users
        container = self.query_one("#user-list", ScrollableContainer)
        container.remove_children()
        if not users:
            self.query_one("#assign-status", Static).update("No users found")
            container.remove_class("visible")
            return
        self.query_one("#assign-status", Static).update(
            f"{len(users)} user(s) — click to assign"
        )
        container.add_class("visible")
        for i, user in enumerate(users[:10]):
            name = user.get("displayName") or user.get("name") or "?"
            email = user.get("emailAddress", "")
            label = f"  {name}  [{email}]" if email else f"  {name}"
            container.mount(Button(label, id=f"user-{i}", classes="user-btn"))

    def _apply(self, account_id: str | None, name: str | None) -> None:
        try:
            if account_id:
                self._client.update_issue(self._issue_key, {"assignee": {"accountId": account_id}})
            elif name:
                self._client.update_issue(self._issue_key, {"assignee": {"name": name}})
            else:
                self._client.update_issue(self._issue_key, {"assignee": None})
            msg = "Assignee removed" if not account_id and not name else "Assignee updated"
            self.app.notify(msg, severity="information")
            self.dismiss(True)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")
