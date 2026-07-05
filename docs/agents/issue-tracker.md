# Issue Tracker: GitHub

Issues for this repo live in GitHub Issues for `elecdot/competehub`. Use the
`gh` CLI for issue operations from inside this clone.

External pull requests are not treated as a triage request surface.

## Issue Forms

Before creating an issue, inspect the local issue forms:

- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/ISSUE_TEMPLATE/task.yml`
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`

If the user asks for a task issue, prefer `task.yml`. Before creating an issue,
preview the title, labels, and body field mapping.

## Operations

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open`
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."`
- Close: `gh issue close <number> --comment "..."`

When a skill says "publish to the issue tracker", create a GitHub issue.

When a skill says "fetch the relevant ticket", read the GitHub issue with
comments and labels.
