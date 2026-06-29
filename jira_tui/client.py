# Copyright (c) 2026 or1k.net
from __future__ import annotations
from typing import Any
from jira import JIRA, JIRAError
from jira.resources import Issue
from .config import Config


class JiraClient:
    def __init__(self, config: Config):
        self._config = config
        self._jira: JIRA | None = None

    def connect(self) -> None:
        cfg = self._config
        # atlassian.net is always Cloud regardless of what's stored in config
        is_cloud = cfg.auth_type == "cloud" or "atlassian.net" in cfg.jira_url
        if is_cloud:
            self._jira = JIRA(
                server=cfg.jira_url,
                basic_auth=(cfg.email, cfg.api_token),
                get_server_info=False,
            )
        else:
            self._jira = JIRA(
                server=cfg.jira_url,
                token_auth=cfg.api_token,
                get_server_info=False,
            )

    @property
    def jira(self) -> JIRA:
        if self._jira is None:
            self.connect()
        return self._jira

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._config.jira_url}{path}"
        resp = self.jira._session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: dict) -> Any:
        url = f"{self._config.jira_url}{path}"
        resp = self.jira._session.post(url, json=json)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, json: dict) -> None:
        url = f"{self._config.jira_url}{path}"
        resp = self.jira._session.put(url, json=json)
        resp.raise_for_status()

    def test_connection(self) -> str:
        user = self.jira.myself()
        return user.get("displayName") or user.get("emailAddress") or user.get("name") or "unknown"

    # ── Projects ─────────────────────────────────────────────────────────────

    def get_projects(self) -> list[dict]:
        projects = self.jira.projects()
        return [{"key": p.key, "name": p.name} for p in projects]

    # ── Issues ───────────────────────────────────────────────────────────────

    ISSUE_FIELDS = "summary,status,priority,assignee,reporter,issuetype,created,updated,description,comment"

    def search_issues(self, jql: str, max_results: int = 50) -> list[Any]:
        # /rest/api/2/search was removed; use the v3 /search/jql endpoint directly
        data = self._get("/rest/api/3/search/jql", params={
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,status,priority,assignee,reporter,issuetype,created,updated",
        })
        return [self._dict_to_issue(i) for i in data.get("issues", [])]

    def get_my_issues(self, max_results: int = 50) -> list[Any]:
        return self.search_issues("assignee = currentUser() ORDER BY updated DESC", max_results)

    def get_project_issues(self, project_key: str, max_results: int = 100) -> list[Any]:
        return self.search_issues(f"project = {project_key} ORDER BY updated DESC", max_results)

    def get_issue(self, issue_key: str) -> Any:
        # Use library for single-issue fetch (still supported via /rest/api/3/issue/{key})
        return self.jira.issue(issue_key)

    # ── Create / Update ──────────────────────────────────────────────────────

    def create_issue(self, fields: dict) -> Any:
        return self.jira.create_issue(fields=fields)

    def update_issue(self, issue_key: str, fields: dict) -> None:
        issue = self.jira.issue(issue_key)
        issue.update(fields=fields)

    # ── Transitions ──────────────────────────────────────────────────────────

    def get_transitions(self, issue_key: str) -> list[dict]:
        transitions = self.jira.transitions(issue_key)
        return [{"id": t["id"], "name": t["name"]} for t in transitions]

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        self.jira.transition_issue(issue_key, transition_id)

    # ── Comments ─────────────────────────────────────────────────────────────

    def get_comments(self, issue_key: str) -> list[Any]:
        return self.jira.comments(issue_key)

    def add_comment(self, issue_key: str, body: str) -> Any:
        return self.jira.add_comment(issue_key, body)

    def delete_comment(self, issue_key: str, comment_id: str) -> None:
        comment = self.jira.comment(issue_key, comment_id)
        comment.delete()

    # ── Users ────────────────────────────────────────────────────────────────

    def get_myself(self) -> dict:
        return self.jira.myself()

    def search_users(self, query: str, issue_key: str = "") -> list[dict]:
        try:
            params: dict = {"query": query, "maxResults": 10}
            if issue_key:
                params["issueKey"] = issue_key
                data = self._get("/rest/api/3/user/assignable/search", params=params)
            else:
                data = self._get("/rest/api/3/user/search", params=params)
            if not isinstance(data, list):
                return []
            return [
                {
                    "accountId": u.get("accountId", ""),
                    "displayName": u.get("displayName", ""),
                    "emailAddress": u.get("emailAddress", ""),
                    "name": u.get("name", ""),
                }
                for u in data
                if u.get("accountId") or u.get("name")
            ]
        except Exception:
            return []

    # ── Issue Meta ───────────────────────────────────────────────────────────

    def get_issue_types(self, project_key: str) -> list[dict]:
        data = self._get(f"/rest/api/3/issue/createmeta/{project_key}/issuetypes")
        return [{"id": t["id"], "name": t["name"]} for t in data.get("issueTypes", [])]

    def get_priorities(self) -> list[dict]:
        try:
            priorities = self.jira.priorities()
            return [{"id": p.id, "name": p.name} for p in priorities]
        except Exception:
            return [
                {"id": "1", "name": "Highest"},
                {"id": "2", "name": "High"},
                {"id": "3", "name": "Medium"},
                {"id": "4", "name": "Low"},
                {"id": "5", "name": "Lowest"},
            ]

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _dict_to_issue(self, raw: dict) -> Any:
        """Wrap a raw /search/jql dict in a lightweight object that matches
        the attribute API used by the rest of the app (issue.key, issue.fields.*)."""
        return _IssueProxy(raw)


class _FieldProxy:
    """Lazy attribute access over a fields dict."""
    def __init__(self, fields: dict):
        self._f = fields

    def __getattr__(self, name: str) -> Any:
        val = self._f.get(name)
        if isinstance(val, dict):
            return _AttrDict(val)
        return val


class _AttrDict:
    """Dict whose keys are accessible as attributes."""
    def __init__(self, d: dict):
        self._d = d

    def __getattr__(self, name: str) -> Any:
        val = self._d.get(name)
        if isinstance(val, dict):
            return _AttrDict(val)
        return val

    def get(self, key, default=None):
        return self._d.get(key, default)


class _IssueProxy:
    def __init__(self, raw: dict):
        self.key: str = raw.get("key", "")
        self.id: str = raw.get("id", "")
        self.fields = _FieldProxy(raw.get("fields", {}))
