# Copyright (c) 2026 or1k.net
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
        max-height: 50;
        border: round $accent;
        background: $surface;
    }
    #create-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1 2 0 2;
    }
    #form-scroll { height: 30; padding: 1 2; }
    .field-label { color: $text-muted; margin-top: 1; }
    #description-area { height: 7; }

    #assignee-dropdown {
        height: auto;
        max-height: 10;
        border: solid $panel;
        background: $background;
        margin: 0 2;
    }
    .assignee-btn {
        width: 1fr; height: 3; margin: 0;
        background: $background; border: none; color: $text;
    }
    .assignee-btn:hover { background: $accent; color: $background; }
    #assignee-status { height: 1; color: $text-muted; padding: 0 2; }

    #error-msg { color: $error; padding: 0 2; height: 1; }
    #btn-row { height: 3; align: center middle; padding: 0 2 1 2; }
    """

    def __init__(self, client: JiraClient, projects: list[dict], **kwargs):
        super().__init__(**kwargs)
        self._client = client
        self._projects = projects
        self._issue_types: list[dict] = []
        self._assignee_id: str = ""
        self._assignee_name: str = ""
        self._assignee_search: str = ""
        self._assignee_users: list[dict] = []
        self._selecting: bool = False
        self._service_desk_id: str = ""
        self._request_type_id: str = ""

    def compose(self) -> ComposeResult:
        with Container(id="create-box"):
            yield Static("Create Issue", id="create-title")
            with ScrollableContainer(id="form-scroll"):
                yield Label("Project *", classes="field-label")
                options = [(f"{p['key']} — {p['name']}", p["key"]) for p in self._projects]
                yield Select(options, id="project-select", prompt="Select project…")

                yield Label("Issue Type *", classes="field-label", id="type-label")
                yield Select([], id="type-select", prompt="Select type…")

                yield Label("Request Type", classes="field-label", id="rt-label")
                yield Select([], id="rt-select", prompt="None (regular issue)")

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

                yield Label("Assignee", classes="field-label")
                yield Input(id="assignee-input", placeholder="Type 2+ chars to search…")

            # Suggestions live OUTSIDE form-scroll so they're always visible
            yield Static("", id="assignee-status")
            yield ScrollableContainer(id="assignee-dropdown")

            yield Static("", id="error-msg")
            with Horizontal(id="btn-row"):
                yield Button("Create [Ctrl+S]", variant="primary", id="create-btn")
                yield Button("Cancel [Esc]", variant="error", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#assignee-dropdown", ScrollableContainer).display = False
        self.query_one("#assignee-status", Static).display = False
        # Request Type is hidden until a JSM project is selected
        self.query_one("#rt-label", Label).display = False
        self.query_one("#rt-select", Select).display = False

    # ── Project / type / request type loading ─────────────────────────────────

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "project-select" and event.value is not Select.BLANK:
            project_key = str(event.value)
            self._service_desk_id = ""
            self._request_type_id = ""
            self._hide_request_types()
            self._load_issue_types(project_key)
            self._load_service_desk(project_key)
        elif event.select.id == "rt-select":
            if event.value is not Select.BLANK:
                self._request_type_id = str(event.value)
                self.query_one("#type-label", Label).update("Issue Type")
            else:
                self._request_type_id = ""
                self.query_one("#type-label", Label).update("Issue Type *")

    def _hide_request_types(self) -> None:
        self.query_one("#rt-label", Label).display = False
        rt = self.query_one("#rt-select", Select)
        rt.display = False
        rt.set_options([])
        self.query_one("#type-label", Label).update("Issue Type *")

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

    @work(thread=True)
    def _load_service_desk(self, project_key: str) -> None:
        desk_id = self._client.get_service_desk_for_project(project_key)
        if not desk_id:
            return
        rt = self._client.get_request_types(desk_id)
        self.app.call_from_thread(self._populate_request_types, desk_id, rt)

    def _populate_request_types(self, desk_id: str, types: list[dict]) -> None:
        if not types:
            return
        self._service_desk_id = desk_id
        rt_sel = self.query_one("#rt-select", Select)
        rt_sel.set_options([(t["name"], t["id"]) for t in types])
        self.query_one("#rt-label", Label).display = True
        rt_sel.display = True
        # Issue Type becomes optional when a request type can be chosen instead
        self.query_one("#type-label", Label).update("Issue Type")

    # ── Assignee live search ──────────────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "assignee-input":
            return
        if self._selecting:
            return
        self._assignee_id = ""
        self._assignee_name = ""
        query = event.value.strip()
        status = self.query_one("#assignee-status", Static)
        dropdown = self.query_one("#assignee-dropdown", ScrollableContainer)
        if len(query) < 2:
            self._assignee_search = ""
            dropdown.display = False
            status.display = False
            return
        if query == self._assignee_search:
            return
        self._assignee_search = query
        dropdown.display = False
        dropdown.remove_children()
        status.update("Searching…")
        status.display = True
        project_key = ""
        try:
            val = self.query_one("#project-select", Select).value
            if val is not Select.BLANK:
                project_key = str(val)
        except Exception:
            pass
        self._search_assignee(query, project_key)

    @work(thread=True)
    def _search_assignee(self, query: str, project_key: str) -> None:
        try:
            users = self._client.search_users(query, project_key=project_key)
            if not users and project_key:
                users = self._client.search_users(query)
            self.app.call_from_thread(self._show_suggestions, query, users)
        except Exception as e:
            self.app.call_from_thread(
                self.query_one("#assignee-status", Static).update, f"Search error: {e}"
            )

    def _show_suggestions(self, query: str, users: list[dict]) -> None:
        if query != self._assignee_search:
            return
        self._assignee_users = users
        status = self.query_one("#assignee-status", Static)
        dropdown = self.query_one("#assignee-dropdown", ScrollableContainer)
        dropdown.remove_children()
        if not users:
            status.update("No users found")
            dropdown.display = False
            return
        status.display = False
        dropdown.display = True
        for i, user in enumerate(users[:8]):
            name = user.get("displayName") or user.get("name") or "?"
            email = user.get("emailAddress", "")
            label = f"  {name}  [{email}]" if email else f"  {name}"
            dropdown.mount(Button(label, id=f"asgn-{i}", classes="assignee-btn"))

    # ── Button handler ────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "create-btn":
            self.action_submit()
        elif btn_id == "cancel-btn":
            self.dismiss(None)
        elif btn_id.startswith("asgn-"):
            idx = int(btn_id[5:])
            user = self._assignee_users[idx]
            self._assignee_id = user.get("accountId", "")
            self._assignee_name = user.get("name", "")
            name = user.get("displayName") or self._assignee_name or "?"
            self._selecting = True
            self.query_one("#assignee-input", Input).value = name
            self._selecting = False
            self._assignee_search = name
            self.query_one("#assignee-dropdown", ScrollableContainer).display = False
            self.query_one("#assignee-status", Static).display = False

    def action_submit(self) -> None:
        error = self.query_one("#error-msg", Static)
        error.update("")

        project_key = self.query_one("#project-select", Select).value
        issue_type_id = self.query_one("#type-select", Select).value
        summary = self.query_one("#summary-input", Input).value.strip()
        description = self.query_one("#description-area", TextArea).text.strip()
        priority = str(self.query_one("#priority-select", Select).value)

        if not project_key or str(project_key) == "Select.BLANK":
            error.update("Project is required")
            return
        if not summary:
            error.update("Summary is required")
            return
        # Issue Type required only when no Request Type chosen
        if not self._request_type_id:
            if not issue_type_id or str(issue_type_id) == "Select.BLANK":
                error.update("Issue type is required (or choose a Request Type)")
                return

        if self._service_desk_id and self._request_type_id:
            self._submit_service_desk(summary, description, priority)
        else:
            self._submit_regular(
                str(project_key), str(issue_type_id), summary, description, priority
            )

    def _submit_service_desk(self, summary: str, description: str, priority: str) -> None:
        error = self.query_one("#error-msg", Static)
        try:
            issue = self._client.create_service_desk_request(
                service_desk_id=self._service_desk_id,
                request_type_id=self._request_type_id,
                summary=summary,
                description=description,
            )
            if not issue.key:
                error.update("Created but no issue key returned")
                return
            # Priority and assignee are set via update after creation —
            # the service desk API only accepts fields defined for the specific request type.
            extra: dict = {}
            if priority:
                extra["priority"] = {"name": priority}
            if self._assignee_id:
                extra["assignee"] = {"accountId": self._assignee_id}
            elif self._assignee_name:
                extra["assignee"] = {"name": self._assignee_name}
            if extra:
                try:
                    self._client.update_issue(issue.key, extra)
                except Exception:
                    pass
            self.app.notify(f"Created {issue.key}", severity="information")
            self.dismiss(issue.key)
        except Exception as e:
            error.update(f"Error: {e}")

    def _submit_regular(self, project_key: str, issue_type_id: str,
                        summary: str, description: str, priority: str) -> None:
        error = self.query_one("#error-msg", Static)
        fields: dict = {
            "project": {"key": project_key},
            "issuetype": {"id": issue_type_id},
            "summary": summary,
        }
        if description:
            fields["description"] = description
        if priority:
            fields["priority"] = {"name": priority}
        if self._assignee_id:
            fields["assignee"] = {"accountId": self._assignee_id}
        elif self._assignee_name:
            fields["assignee"] = {"name": self._assignee_name}
        try:
            issue = self._client.create_issue(fields)
            self.app.notify(f"Created {issue.key}", severity="information")
            self.dismiss(issue.key)
        except Exception as e:
            error.update(f"Error: {e}")
