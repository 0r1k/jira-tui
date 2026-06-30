# Jira TUI

Terminal-based Jira task manager. Connect to one or more Jira instances, browse issues, create, transition, comment, and reassign — all without leaving the terminal.

---

## Requirements

- Python 3.10+
- Jira Cloud **or** Jira Server / Data Center
- API token (Cloud) or Personal Access Token (Server)

---

## Installation

```bash
# Clone or download the project, then:
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running

```bash
venv/bin/python main.py
```

On first launch the **Connections** screen opens automatically. Add at least one Jira instance and press **Test & Save**.

---

## Connections Screen

Opened automatically on first run, or via `s` at any time.

```
⚙  Jira TUI © or1k.net — Connections
┌──────────────────────────────────────────────────────────┐
│  yourcompany.atlassian.net          [Delete]          │
│  another-workspace.atlassian.net      [Delete]          │
│                                                          │
│              [Add Jira]   [Close]                        │
└──────────────────────────────────────────────────────────┘
```

- **Add Jira** — opens the credential form for a new instance
- Click a domain row to **edit** its credentials
- **Delete** — asks for confirmation then removes the instance

### Credential form fields

| Field | Description |
|---|---|
| Auth type | Cloud (email + API token) or Server/DC (PAT) |
| Jira URL | Full URL, e.g. `https://yourcompany.atlassian.net` |
| Email | Your Atlassian account email (Cloud only) |
| API token / PAT | Token copied from Jira or Atlassian account |

Press **Test & Save** to verify the connection and save. Press **Cancel** or `Esc` to discard.

> URLs containing `atlassian.net` automatically switch the auth type to Cloud.

### Getting an API token

**Cloud:** https://id.atlassian.com/manage-profile/security/api-tokens → Create API token

**Server / Data Center:** Profile → Personal Access Tokens → Create token

The config is saved to `~/.config/jira-tui/config.json` with mode `600`.

---

## Main Screen

```
┌─ ⚡ Jira TUI © or1k.net ─────────────────────────────────────────────────┐
│ Navigation                 ▌ My Issues  (69 issues)                       │
│  ● jiraworkspace1...       │ ┌──────────────────────────────────────────┐ │
│    👤 My Issues            │ │ Key      Type  Summary        Status  Pri │ │
│    📋 Reported by me       │ │ ITSD-760 Task  Setup deploy…  Invalid 🟡  │ │
│    👀 Watching             │ │ ITSD-744 Task  Setup deploy…  Backlog 🟡  │ │
│    🔍 Search (JQL)         │ └──────────────────────────────────────────┘ │
│    📁 Projects             │                                               │
│       ITSD  Helpdesk team  │                                               │
│       TPT   Topretopt      │                                               │
│  ● jiraworkspace2...       │                                               │
│    👤 My Issues            │                                               │
├────────────────────────────┴──────────────────────────────────────────────┤
│  n New Issue  f Search  r Refresh  s Settings  Enter Open  ? Help  q Quit │
└───────────────────────────────────────────────────────────────────────────┘
```

### Sidebar navigation

Each configured Jira appears as a top-level node (showing the domain without `https://`). Under each node:

| Item | Shows |
|---|---|
| 👤 My Issues | Issues assigned to you, sorted by last updated |
| 📋 Reported by me | Issues you created |
| 👀 Watching | Issues you are watching |
| 🔍 Search (JQL) | Opens the JQL search screen for this Jira |
| 📁 Projects → KEY | All issues in that project |

**Sidebar width** is adjustable: drag the `▌` handle between the sidebar and the issue list with the mouse.

### Keyboard shortcuts

| Key | Action |
|---|---|
| `↑` `↓` | Move cursor through the issue list |
| `Enter` | Open selected issue |
| `n` | Create new issue |
| `f` | Open JQL search |
| `r` | Refresh current view |
| `s` | Open connections/settings |
| `?` | Show help |
| `q` | Quit |

The footer bar at the bottom is **clickable** — you can also click any shortcut label with the mouse.

---

## Issue Detail Screen

Opens when you press `Enter` on an issue or click a row.

```
ITSD-760  Setup deploy from Gitlab and add Wildcard SSL
Task │ Status: In Progress │ Priority: 🟡 Medium │ Assignee: Your Name │ Reporter: …
──────────────────────────────────────┬──────────────────────────────────
 Description                          │ Comments  (newest first)
                                      │ John Doe  2026-05-10  Done on staging.
 Setup deploy from Gitlab…            │ Jane      2026-05-09  Started work.
──────────────────────────────────────┴──────────────────────────────────
 Esc Back  t Transition  c Comment  a Assign  e Edit Summary  r Refresh
```

| Key | Action |
|---|---|
| `t` | **Transition** — change issue status |
| `c` | **Comment** — add a comment |
| `a` | **Assign** — reassign the issue |
| `e` | **Edit summary** — change the issue title |
| `r` | Refresh the issue (reload from Jira) |
| `Esc` | Go back to the issue list |

Comments are displayed **newest-first** in a compact single-line format.

---

## Transition Modal

Appears after pressing `t`. Shows all available status transitions as styled buttons.

- Click a transition button to apply it
- Press **Cancel** or `Esc` to go back without changing anything

---

## Assign Modal

Appears after pressing `a` on an issue.

```
Assign  ITSD-760
┌──────────────────────────────────────────────────┐
│ [Type name to search…                          ] │
│ Start typing (2+ chars) to see suggestions       │
│ ┌──────────────────────────────────────────────┐ │
│ │   Your Name  [you@company.com]             │ │
│ │   John Doe     [john@company.com]            │ │
│ └──────────────────────────────────────────────┘ │
│  [Assign to me]  [Remove assignee]  [Cancel]     │
└──────────────────────────────────────────────────┘
```

- Type 2+ characters to search users by name
- Results appear as a live dropdown — click to assign
- **Assign to me** — assigns the issue to the currently logged-in user
- **Remove assignee** — clears the assignee field
- `Esc` — cancel

---

## Comment Modal

Appears after pressing `c`.

- Type your comment in the text area
- Press **Submit** or `Ctrl+S` to post
- Press **Cancel** or `Esc` to discard

---

## Create Issue Screen

Appears after pressing `n`.

| Field | Required | Notes |
|---|---|---|
| Project | yes | Select from dropdown; loads issue types automatically |
| Issue Type | yes | Loaded after project is selected |
| Summary | yes | One-line title |
| Description | no | Multi-line free text |
| Priority | no | Highest / High / Medium / Low / Lowest |
| Assignee | no | Type 2+ chars for live user search dropdown |

Press **Create** or `Ctrl+S` to submit. Press **Cancel** or `Esc` to discard.

> If the project shows "No create permission", your Jira account does not have the right to create issues there.

---

## JQL Search Screen

Appears after pressing `f` or clicking 🔍 Search in the sidebar.

Enter any valid JQL query and press `Enter` or click **Search**:

```
assignee = currentUser() AND status = "In Progress"
project = ITSD AND priority = High ORDER BY created DESC
text ~ "deploy" AND updated >= -7d
```

Results appear in a table. Press `Enter` on a row to open the issue detail. Press **Back** or `Esc` to return.

### Useful JQL examples

```
# My open issues
assignee = currentUser() AND statusCategory != Done

# Issues updated this week
project = ITSD AND updated >= startOfWeek()

# High priority bugs
issuetype = Bug AND priority in (High, Highest) AND status != Done

# Issues assigned to me in a sprint
assignee = currentUser() AND sprint in openSprints()
```

---

## Global shortcuts

| Key | Action |
|---|---|
| `Ctrl+A` | Select all text in any focused input or textarea |

---

## Priority icons

| Icon | Priority |
|---|---|
| 🔴 | Highest |
| 🟠 | High |
| 🟡 | Medium |
| 🔵 | Low |
| ⚪ | Lowest |

---

## Project structure

```
task_manager/
├── main.py                        # Entry point
├── requirements.txt
└── jira_tui/
    ├── config.py                  # JiraConfig + MultiConfig; saves ~/.config/jira-tui/config.json
    ├── client.py                  # Jira REST API v3 wrapper
    └── screens/
        ├── setup.py               # JiraListScreen + JiraEditScreen (multi-connection management)
        ├── main_screen.py         # Issue list + multi-Jira sidebar + resizable handle
        ├── issue_detail.py        # Issue detail + Transition/Comment/Assign/Edit modals
        ├── create_issue.py        # New issue form with live assignee autocomplete
        └── search_screen.py       # JQL search
```

---

## Config file format

The config is managed through the UI but can also be edited manually:

```json
{
  "jiras": [
    {
      "jira_url": "https://yourcompany.atlassian.net",
      "email": "you@yourcompany.com",
      "api_token": "ATATT3xFfGF0...",
      "auth_type": "cloud"
    },
    {
      "jira_url": "https://jira.yourcompany.com",
      "email": "",
      "api_token": "NjA4ODY5...",
      "auth_type": "server"
    }
  ]
}
```

> Old single-instance format (`jira_url` at the top level) is automatically migrated on first load.

---

## Troubleshooting

**403 Failed to parse Connect Session Auth Token**
`auth_type` is set to `server` but the URL is `atlassian.net` (Cloud). Open Settings (`s`), click the instance, and re-save — Cloud URLs are detected automatically.

**410 The requested API has been removed**
Jira Cloud removed `/rest/api/2/search`. This app uses `/rest/api/3/search/jql`. Make sure you're running the latest version.

**No create permission for PROJECT**
Your account does not have "Create Issues" permission in that project. Choose a different project or ask your Jira admin.

**Issue types not loading**
Select a project first — issue types are loaded on demand after project selection.

**Assignee search returns no results**
The search uses `/rest/api/3/user/assignable/search` scoped to the issue or project. Try a shorter query (first name only). If the project key is not yet selected in Create Issue, results may be limited.

---

© 2026 [or1k.net](https://or1k.net)
