# Member Help Patterns

Use these as optional patterns. Keep the live answer short and tailored.

## Assignment Recovery

Use when the member knows their identity but cannot locate assigned work.

Ask first:

```text
你今天站会分配到的 issue 或 owner list 是什么？贴 issue 编号或相关行即可。
```

If unavailable, use GitHub issue metadata to find candidates and state that this
is recovery, not reassignment.

## Issue Understanding

Use when the member has an issue but does not understand it.

Cover:

- what this issue is trying to complete
- what is in scope and out of scope
- what acceptance criteria mean
- which docs matter first
- the next action

Prompt:

```text
/member-help 我是成员 c，站会分配给我的 issue 是 #12。我看不懂目标和验收标准，请帮我对齐上下文并告诉我下一步。
```

## Git Help

Use when the member is blocked by branch, commit, or PR mechanics.

Read `README-GIT.md`. Give only the commands or naming guidance needed for the
current situation.

Prompt:

```text
/member-help 我是成员 c，负责 issue #12。我不会为这个任务开分支和准备提交，请按 README-GIT 给我最小步骤。
```

## Validation Help

Use when the member does not know how to prove the work is done.

Read the issue affected surfaces and `docs/project_workflow.md`. Use the
validation matrix from `AGENTS.md` or project docs.

Prompt:

```text
/member-help 我是成员 c，负责 issue #12。我已经完成改动，但不知道应该跑哪些验证。
```

## PR Help

Use when the member has changes and needs to prepare a PR.

Prefer a short PR checklist and draft summary. Do not create or edit the PR
unless explicitly asked and confirmed.

Prompt:

```text
/member-help 我是成员 c，负责 issue #12。我准备提 PR，请帮我整理 summary、validation、risk 和 follow-up。
```

## Review Help

Use when review comments are unclear.

Read only the relevant review comments first. Read diff or logs only when needed.

Classify comments as:

- must fix
- optional suggestion
- needs clarification

Prompt:

```text
/member-help 我是成员 c，PR #18 被 review 打回。请帮我整理必须修改、可选建议和需要确认的问题。
```

## Agent Usage Help

Use when the member does not know how to ask the agent.

Give one copyable prompt that points to the right workflow and includes member,
issue, goal, and boundary.
