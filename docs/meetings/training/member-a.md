# Member A Workflow Drill

## Assignment

- Member: a
- Practice issue: #12 docs(meetings): record member a standup example row plan
- DRI: a
- Reviewer: f
- Validation owner: a
- Peer-check member: b
- Docs impact: `docs/meetings/training/member-a.md` only

## Source Documents Read

- CONTRIBUTING.md
- README-GIT.md
- docs/project_workflow.md
- docs/meetings/daily-standup-template.md
- docs/meetings/2026-07-08-standup-0.md

## Proposed Work Record

- Target surface: `docs/meetings/training/member-a.md`
- Proposed change if this were a real docs or skill edit: record a proposed
  standup owner-list row plan for member a's assigned issue.
- Why this is safe: this is a training-only record and does not change product
  behavior, shared workflow rules, issue ownership, or the official standup
  assignment.
- Why this training issue does not change the shared target surface: the change
  is limited to member a's drill file under `docs/meetings/training/`.

## Workflow Plan

- Branch name: `docs/member-a-standup-drill`
- Commit message: `docs(meetings): record member a workflow drill`
- PR summary draft: Record member a's standup owner-list training plan for
  issue #12.
- Validation command: `just docs-build`
- Peer-check plan: ask member b to confirm that this record matches the
  standup assignment and stays limited to member a's training file.

## Questions Or Blockers

- None.

## Validation

- [x] `just docs-build` equivalent strict MkDocs build completed through Git
      Bash because the local `just` shell could not find `uv`.
- [x] Manual review: this record is training-only and does not change shared
      project behavior, workflow rules, or product scope.
