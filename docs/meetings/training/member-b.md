# Member B Workflow Drill

## Assignment

- Member: b
- Practice issue: [#13 docs(contributing): record member b member-help example plan](https://github.com/elecdot/competehub/issues/13)
- DRI: b
- Reviewer: f
- Validation owner: b
- Peer-check member: c
- Docs impact: `docs/meetings/training/member-b.md` only

## Source Documents Read

- `CONTRIBUTING.md`
- `README-GIT.md`
- `docs/project_workflow.md`
- `.agents/skills/member-help/SKILL.md`
- `docs/meetings/2026-07-08-standup-0.md`

## Proposed Work Record

- Target surface: `CONTRIBUTING.md`
- Proposed change if this were a real docs edit: add a short `/member-help`
  usage example for a member who already has a standup-assigned issue and needs
  help recovering context, boundaries, and next action.
- Why this is safe: the example asks for orientation and next-step guidance
  only. It does not ask the agent to reassign work, edit shared workflow rules,
  create commits, push branches, open pull requests, or perform external writes.
- Why this training issue does not change the shared target surface: issue #13
  is a record-only workflow drill. It explicitly limits the docs impact to this
  personal training file and says not to modify `CONTRIBUTING.md` or
  `.agents/skills/member-help/SKILL.md`.

## Proposed Member-Help Example

```text
/member-help 我是成员 b，今天站会分配给我的 issue 是 #13：
docs(contributing): record member b member-help example plan。

我需要先对齐这个 issue 的目标、范围、不能改的文件、验证方式和下一步。
请帮我：

1. 用自己的话解释这个 issue 要完成什么；
2. 列出 in scope 和 out of scope；
3. 告诉我应该先读哪些项目文件；
4. 把 completion checklist 转成我接下来能执行的步骤；
5. 给出最小的分支名、提交信息、PR 摘要和验证命令；
6. 明确这只是帮助我继续已分配工作，不重新分配任务，也不替我直接做外部写入。
```

## When To Use It

Use this example when member b already has an assigned GitHub issue or standup
owner-list row, but needs help understanding the objective, source documents,
scope limits, validation plan, and next action.

Do not use it to find a new assignment, reassign ownership, change
`CONTRIBUTING.md`, change member-help behavior, create or update GitHub issues,
commit changes, push branches, or open a pull request. If member b later wants
implementation or GitHub writes, switch to the appropriate project workflow and
follow `AGENTS.md`.

## Workflow Plan

- Branch name: `docs/member-b-member-help-13`
- Commit message: `docs(contributing): record member b member-help example plan`
- PR summary draft:
  - Add member b's training record for issue #13.
  - Record a proposed `/member-help` usage example for an assigned issue.
  - Explain why shared contributor and skill documents are intentionally
    unchanged.
- Validation command: `just docs-build`
- Peer-check plan: ask member c to read this training record before reviewer
  handoff and confirm that the example preserves member-help boundaries.

## Peer-Check Request

```text
成员 c，请帮我 peer-check issue #13 的训练记录：
docs/meetings/training/member-b.md

重点看：
1. proposed member-help example 是否只帮助成员 b 理解并继续已分配 issue；
2. 是否没有把 member-help 变成重新分配、代做、提交、推送或开 PR 的流程；
3. 是否清楚说明为什么不修改 CONTRIBUTING.md 和 .agents/skills/member-help/SKILL.md。
```

Peer-check status: pending member c review before reviewer handoff.

## Questions Or Blockers

- None.

## Validation

- [x] `just docs-build` equivalent strict MkDocs build completed through a
      repository-local Python virtual environment because `just` and `uv` were
      not available on this machine.
- [x] Manual review: this record is training-only and does not change shared
      project behavior, workflow rules, member-help behavior, or product scope.
