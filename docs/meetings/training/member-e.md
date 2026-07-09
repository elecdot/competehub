# Member E Workflow Drill

## Assignment

- Member: e
- Practice issue: [#16 docs(agents): record member e validation-help prompt plan](https://github.com/elecdot/competehub/issues/16)
- DRI: e
- Reviewer: f
- Validation owner: e
- Peer-check member: a
- Docs impact: `docs/meetings/training/member-e.md` only

## Source Documents Read

- `AGENTS.md`
- `CONTRIBUTING.md`
- `README.md`
- `README-GIT.md`
- `docs/project_workflow.md`
- `docs/meetings/2026-07-08-standup-0.md`
- `.agents/skills/member-help/SKILL.md`
- `.agents/skills/member-help/references/patterns.md`
- GitHub Issue [#16](https://github.com/elecdot/competehub/issues/16)

## Proposed Work Record

- Target surface: `.agents/skills/member-help/references/patterns.md`
- Proposed change if this were a real docs or skill edit: add a safer, more explicit validation-help prompt for members who have completed their assigned change but do not know how to prove it is done.
- Why this is safe: the prompt asks the agent to map the issue's affected surfaces to the repository validation matrix and to identify the smallest relevant checks. It keeps the member as validation owner and does not ask the agent to replace review, mark work complete, commit, push, open a PR, or perform external writes.
- Why this training issue does not change the shared target surface: issue #16 is a record-only workflow training slice. It explicitly limits the docs impact to `docs/meetings/training/member-e.md` only, so the shared member-help skill reference, routing rules, workflow rules, business code, product docs, architecture docs, API docs, data model docs, and issue templates remain unchanged.

## Proposed Validation-Help Prompt

```text
/member-help I am member e, responsible for issue #<issue-number>. I have
finished the change, but I do not know how to prove the work is done. Please
use the member-help validation-help pattern to help me prepare a validation
plan:

1. Read the issue affected surfaces and identify what needs validation.
2. Compare those surfaces with the validation matrix in AGENTS.md and
   docs/project_workflow.md.
3. List the smallest sufficient validation commands I should run.
4. Separate required checks, checks I may skip with a reason, and manual review
   evidence.
5. Draft a short PR validation note I can reuse.
6. Confirm that I remain the validation owner, and do not update issue state,
   commit, push, or create a PR for me.
```

## When To Use It

Use this prompt when member e already has an assigned issue and has finished or nearly finished the change, but needs help choosing validation evidence that matches the affected surfaces.

Do not use it to reassign validation ownership, bypass reviewer judgment, change shared skill references, change workflow rules, mark GitHub issues complete, commit, push, or create a PR. If the member asks for implementation or external writes after the validation plan is clear, switch to the appropriate project workflow and follow `AGENTS.md`.

## Workflow Plan

- Branch name: `docs/member-e-validation-help-record`
- Commit message: `docs(agents): record member e validation-help prompt plan`
- PR summary draft:
  - Add member e's training record for issue #16.
  - Record a proposed validation-help prompt for member-help.
  - Explain why the shared member-help reference and project behavior are intentionally unchanged.
- Validation command: `just docs-build`
- Peer-check plan: ask member a to review workflow consistency before reviewer handoff to f.

## Peer-Check Request

```text
Member a, please peer-check the issue #16 training record:
docs/meetings/training/member-e.md

Please focus on:
1. whether the proposed validation-help prompt only helps the member choose
   validation evidence;
2. whether it keeps e as validation owner and does not let member-help replace
   acceptance, reviewer judgment, or external writes;
3. whether it clearly explains why
   .agents/skills/member-help/references/patterns.md is not changed.
```

Peer-check status: planned before reviewer handoff.

## Questions Or Blockers

- None.

## Validation

- [ ] `just docs-build`
  - Result: failed before documentation build because `just` is not installed.
- [x] Manual review: this record is training-only and does not change shared project behavior, workflow rules, member-help behavior, or product scope.
