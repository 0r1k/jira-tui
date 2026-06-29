# Jira TUI

Terminal-based Jira task manager. Connects to your Jira account, shows issues, lets you create, transition, and comment on them — all without leaving the terminal.

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

## Configuration

### Jira Cloud (atlassian.net)

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**, give it a name, copy the token
3. Create `~/.config/jira-tui/config.json`:

```json
{
  "jira_url": "https://yourcompany.atlassian.net",
  "email": "you@yourcompany.com",
  "api_token": "ATATT3xFfGF0...",
  "auth_type": "cloud",
  "default_project": ""
}
```

### Jira Server / Data Center (self-hosted)

1. In Jira: **Profile → Personal Access Tokens → Create token**
2. Create `~/.config/jira-tui/config.json`:

```json
{
  "jira_url": "https://jira.yourcompany.com",
  "email": "",
  "api_token": "NjA4ODY5...",
  "auth_type": "server",
  "default_project": ""
}
```

> **Note:** For Server auth the `email` field is not used and can be left empty.

The config file is created automatically with mode `600` when you save settings through the built-in setup screen (press `S` in the app).

---

## Running

```bash
venv/bin/python main.py
```

On first launch (no config found) the **Setup screen** opens automatically.

---

## Setup Screen

Opened automatically on first run, or via `S` at any time.

| Field | Description |
|---|---|
| Auth type | Cloud (email + API token) or Server/DC (PAT) |
| Jira URL | Full URL, e.g. `https://yourcompany.atlassian.net` |
| Email | Your Atlassian account email (Cloud only) |
| API token / PAT | Token copied from Jira or Atlassian account |

Press **Test & Save** to verify the connection and write the config. Press **Cancel** or `Esc` to discard.

> URLs containing `atlassian.net` automatically switch the auth type to Cloud.

---

## Main Screen

```
┌─ ⚡ Jira TUI © or1k.net ────────────────────────────────────────────────┐
│ Navigation       │ My Issues  (69 issues)                               │
│  👤 My Issues    │ ┌─────────────────────────────────────────────────┐  │
│  📋 Reported     │ │ Key      Type   Summary          Status   Pri   │  │
│  👀 Watching     │ │ ITSD-760 Task   Setup deploy...  Invalid  🟡Med │  │
│  🔍 Search       │ │ ITSD-744 Task   Setup deploy...  Backlog  🟡Med │  │
│  📁 Projects     │ └─────────────────────────────────────────────────┘  │
│    ITSD          │                                                       │
│    CNT           │                                                       │
├──────────────────┴───────────────────────────────────────────────────────┤
│  n New Issue  f Search  r Refresh  s Settings  Enter Open  ? Help  q Quit│
└──────────────────────────────────────────────────────────────────────────┘
```

### Sidebar navigation

Click or press `Enter` on any item in the left panel:

| Item | Shows |
|---|---|
| 👤 My Issues | Issues assigned to you, sorted by last updated |
| 📋 Reported by me | Issues you created |
| 👀 Watching | Issues you are watching |
| 🔍 Search (JQL) | Opens the JQL search screen |
| 📁 Projects → KEY | All issues in that project |

### Keyboard shortcuts

| Key | Action |
|---|---|
| `↑` `↓` | Move cursor through the issue list |
| `Enter` | Open selected issue |
| `n` | Create new issue |
| `f` | Open JQL search |
| `r` | Refresh current view |
| `s` | Open settings |
| `?` | Show help |
| `q` | Quit |

The footer bar at the bottom is **clickable** — you can also click any shortcut label with the mouse.

---

## Issue Detail Screen

Opens when you press `Enter` on an issue or click a row.

```
ITSD-760  Setup deploy from Gitlab and add Wildcard SSL
Task │ Status: Invalid │ Priority: 🟡 Medium │ Assignee: Oleh Kurudz │ Reporter: ...
──────────────────────────────────────┬───────────────────────────
 Description                          │ Comments
                                      │ ┌──────────────────────┐
 Setup deploy from Gitlab...          │ │ John Doe  2026-05-10  │
                                      │ │ Done on staging.      │
                                      │ └──────────────────────┘
──────────────────────────────────────┴───────────────────────────
 Esc Back  t Transition  c Comment  e Edit Summary  r Refresh
```

| Key | Action |
|---|---|
| `t` | **Transition** — change issue status (To Do / In Progress / Done / etc.) |
| `c` | **Comment** — add a comment |
| `e` | **Edit summary** — change the issue title |
| `r` | Refresh the issue (reload from Jira) |
| `Esc` | Go back to the issue list |

---

## Transition Modal

Appears after pressing `t`. Shows all available status transitions for the issue.

- Click a transition button to apply it
- Press **Cancel** or `Esc` to go back without changing anything

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
| Description | no | Multi-line |
| Priority | no | Highest / High / Medium / Low / Lowest |
| Assignee | no | Enter email or username; left blank = unassigned |

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
    ├── config.py                  # Loads/saves ~/.config/jira-tui/config.json
    ├── client.py                  # Jira REST API wrapper (v3)
    └── screens/
        ├── setup.py               # Auth setup screen
        ├── main_screen.py         # Issue list + sidebar
        ├── issue_detail.py        # Issue detail + Transition/Comment/Edit modals
        ├── create_issue.py        # New issue form
        └── search_screen.py       # JQL search
```

---

## Troubleshooting

**403 Failed to parse Connect Session Auth Token**
Your `auth_type` is set to `server` but your URL is `atlassian.net` (Cloud). Open Settings (`s`) and re-save — the app detects Cloud URLs automatically.

**410 The requested API has been removed**
Jira Cloud removed `/rest/api/2/search`. This app uses the current `/rest/api/3/search/jql` endpoint. If you see this, make sure you are running the latest version of the code.

**No create permission for PROJECT**
Your account does not have the "Create Issues" permission in that project. Choose a different project or ask your Jira admin.

**Issue types not loading**
Select a project first — issue types are loaded on demand after a project is chosen.

---

© 2026 [or1k.net](https://or1k.net)
