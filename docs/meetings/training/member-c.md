# Member C Workflow Drill

## Assignment

- Member: c (马悦鑫)
- Practice issue: [#14 docs(agents): record member c issue-understanding prompt plan](https://github.com/elecdot/competehub/issues/14)
- DRI: c
- Reviewer: f
- Validation owner: c
- Peer-check member: d
- Docs impact: `docs/meetings/training/member-c.md` only

## Source Documents Read

- `CONTRIBUTING.md`
- `README-GIT.md`
- `docs/project_workflow.md`
- `.agents/skills/member-help/SKILL.md`
- `.agents/skills/member-help/references/patterns.md`
- `docs/meetings/2026-07-08-standup-0.md`

## Proposed Work Record

- Target surface: `.agents/skills/member-help/references/patterns.md`
- Proposed change if this were a real skill-reference edit: add a safer, more explicit issue-understanding prompt for members who have an assigned issue but do not yet understand the goal, scope, acceptance criteria, or next action.
- Why this is safe: the prompt asks for context alignment and next-step guidance, not reassignment, direct implementation, GitHub writes, commits, pushes, or PR creation.
- Why this training issue does not change the shared target surface: issue #14 is a record-only workflow training slice. It explicitly says to create only this training file and not modify member-help behavior, routing rules, shared skill references, business code, product docs, architecture docs, API docs, data model docs, issue templates, or workflow rules.

## Proposed Issue-Understanding Prompt

```text
/member-help 我是成员 c，站会分配给我的 issue 是 #<issue-number>。我已经读过 issue，
但还不确定目标、范围、验收标准和下一步。请按 member-help 的 issue-understanding
模式帮我对齐上下文：

1. 用自己的话解释这个 issue 要完成什么；
2. 划清 in scope 和 out of scope；
3. 把 completion checklist 转成我下一步可以执行的行动；
4. 指出我应该先读哪些项目文档或文件；
5. 给出最小的分支、验证和 peer-check 路径；
6. 明确哪些事需要人类确认，哪些事不能让 agent 直接代做。
```

## When To Use It

Use this prompt when member c already has an assigned issue from the standup or GitHub issue tracker, but does not yet understand the objective, boundaries, acceptance criteria, source documents, or next action.

Do not use it to find a new assignment, reassign work, edit shared workflow documents, open or update GitHub issues, create commits, push branches, or prepare a PR. If the member wants implementation or GitHub writes after the issue is understood, switch to the appropriate project workflow and follow `AGENTS.md`.

## Workflow Plan

- Branch name: `docs/member-c-issue-understanding-14`
- Commit message: `docs(agents): record member c issue-understanding prompt plan`
- PR summary draft:
  - Add member c's training record for issue #14.
  - Record a proposed issue-understanding prompt for member-help.
  - Explain why the shared member-help reference is intentionally unchanged.
- Validation command: `just docs-build`
- Peer-check plan: ask member d to read this training record before reviewer handoff and confirm that the prompt preserves member-help boundaries.

## Peer-Check Request

```text
成员 d，请帮我 peer-check issue #14 的训练记录：
docs/meetings/training/member-c.md

重点看：
1. proposed issue-understanding prompt 是否只帮助成员理解 issue；
2. 是否没有把 member-help 变成代做、重分配或外部写入流程；
3. 是否清楚说明为什么不修改 .agents/skills/member-help/references/patterns.md。
```

Peer-check status: completed before reviewer handoff, confirmed by member c.

## Questions Or Blockers

- None.

## Validation

- [x] `just docs-build`
  - Result: passed locally; documentation built successfully.
- [x] Manual review: this record is training-only and does not change shared project behavior, workflow rules, member-help behavior, or product scope.
