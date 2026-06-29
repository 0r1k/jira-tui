from __future__ import annotations
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static, TextArea
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.binding import Binding
from textual import work
from ..client import JiraClient


class CreateIssueScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Cancel"),
        Binding("ctrl+s", "submit", "Create"),
    ]

    CSS = """
    CreateIssueScreen { align: center middle; }
    #create-box {
        width: 72;
        height: auto;
        max-height: 38;
        border: round $accent;
        background: $surface;
    }
    #create-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1 2 0 2;
    }
    #form-scroll { height: 28; padding: 1 2; }
    .field-label { color: $text-muted; margin-top: 1; }
    #description-area { height: 7; }
    #error-msg { color: $error; padding: 0 2; height: 1; }
    #btn-row { height: 3; align: center middle; padding: 0 2 1 2; }
    """

    def __init__(self, client: JiraClient, projects: list[dict], **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._projects = projects
        self._issue_types: list[dict] = []

    def compose(self) -> ComposeResult:
        with Container(id="create-box"):
            yield Static("Create Issue", id="create-title")
            with ScrollableContainer(id="form-scroll"):
                yield Label("Project *", classes="field-label")
                options = [(f"{p['key']} — {p['name']}", p["key"]) for p in self._projects]
                yield Select(options, id="project-select", prompt="Select project…")

                yield Label("Issue Type *", classes="field-label")
                yield Select([], id="type-select", prompt="Select type…")

                yield Label("Summary *", classes="field-label")
                yield Input(id="summary-input", placeholder="Brief one-line summary")

                yield Label("Description", classes="field-label")
                yield TextArea(id="description-area")

                yield Label("Priority", classes="field-label")
                yield Select(
                    [("Highest", "Highest"), ("High", "High"), ("Medium", "Medium"),
                     ("Low", "Low"), ("Lowest", "Lowest")],
                    value="Medium",
                    id="priority-select",
                )

                yield Label("Assignee (email/username)", classes="field-label")
                yield Input(id="assignee-input", placeholder="leave empty for unassigned")

            yield Static("", id="error-msg")
            with Horizontal(id="btn-row"):
                yield Button("Create [Ctrl+S]", variant="primary", id="create-btn")
                yield Button("Cancel [Esc]", variant="error", id="cancel-btn")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "project-select" and event.value is not Select.BLANK:
            self._load_issue_types(str(event.value))

    @work(thread=True)
    def _load_issue_types(self, project_key: str) -> None:
        try:
            types = self._client.get_issue_types(project_key)
            self.app.call_from_thread(self._populate_types, types)
        except Exception as e:
            msg = str(e)
            if "cannot create" in msg.lower() or "404" in msg:
                self.app.call_from_thread(
                    self.query_one("#error-msg", Static).update,
                    f"No create permission for {project_key}",
                )
            else:
                self.app.call_from_thread(
                    self.query_one("#error-msg", Static).update,
                    f"Failed to load issue types: {e}",
                )

    def _populate_types(self, types: list[dict]) -> None:
        self._issue_types = types
        sel = self.query_one("#type-select", Select)
        sel.set_options([(t["name"], t["id"]) for t in types])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_submit(self) -> None:
        error = self.query_one("#error-msg", Static)
        error.update("")

        project_key = self.query_one("#project-select", Select).value
        issue_type_id = self.query_one("#type-select", Select).value
        summary = self.query_one("#summary-input", Input).value.strip()
        description = self.query_one("#description-area", TextArea).text.strip()
        priority = str(self.query_one("#priority-select", Select).value)
        assignee_raw = self.query_one("#assignee-input", Input).value.strip()

        if not project_key or str(project_key) == "Select.BLANK":
            error.update("Project is required")
            return
        if not issue_type_id or str(issue_type_id) == "Select.BLANK":
            error.update("Issue type is required")
            return
        if not summary:
            error.update("Summary is required")
            return

        fields: dict = {
            "project": {"key": str(project_key)},
            "issuetype": {"id": str(issue_type_id)},
            "summary": summary,
        }
        if description:
            fields["description"] = description
        if priority:
            fields["priority"] = {"name": priority}
        if assignee_raw:
            # Try accountId first (Cloud), fall back to name (Server)
            users = self._client.search_users(assignee_raw)
            if users:
                fields["assignee"] = {"accountId": users[0]["accountId"]}
            else:
                fields["assignee"] = {"name": assignee_raw}

        try:
            issue = self._client.create_issue(fields)
            self.app.notify(f"Created {issue.key}", severity="information")
            self.dismiss(issue.key)
        except Exception as e:
            error.update(f"Error: {e}")
