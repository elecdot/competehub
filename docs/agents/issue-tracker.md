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

## Delivery Ownership

CompeteHub issues must follow the Delivery Ownership rules in
`docs/project_workflow.md`. This applies even when another skill, such as
`to-issues`, provides a generic issue body template. The skill may decide the
vertical slice shape, but the published issue must still include the repository
fields from `.github/ISSUE_TEMPLATE/task.yml`.

For task issues, include this field in the preview and issue body:

```text
Delivery Ownership:
DRI:
Contributors:
Reviewer:
Validation owner:
Docs impact:
```

Fill it with these defaults:

- `DRI`: one concrete member or role, usually the primary module owner from
  `docs/reports/module_breakdown_v1.0.md`; do not use multiple DRIs.
- `Contributors`: only materially related members, typed as `Active`,
  `Align with`, or `FYI`. Do not list all a-f for ordinary implementation
  issues.
- `Reviewer`: usually `f` or the relevant tech/product/repo-admin role; avoid
  matching the DRI except for small documentation or process fixes.
- `Validation owner`: a human member or role, not an agent.
- `Docs impact`: concrete documentation paths, or
  `None - explicitly reviewed`.

If the DRI or other ownership fields cannot be inferred, preview the candidates
or `TBD`, ask the user to confirm, and do not label the issue `ready-for-agent`
until the ownership is complete.

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
