# Member d Meeting Workflow Training

## Sources Read

- `CONTRIBUTING.md`
- `README-GIT.md`
- `docs/project_workflow.md`
- `docs/meetings/README.md`
- `docs/meetings/daily-standup-template.md`

## Proposed Blocker Note Example

Issue: #15
DRI: d
Status: blocked
Blocker: I do not yet understand whether a blocker note should update the standup template or only reference the related GitHub Issue.
Next action: Ask f to confirm the safe format, then record the example in this personal training file only.

## Why This Is Safe

This note is safe because it does not change the shared meeting template or meeting governance. It records a proposed blocker example in a personal training file, while keeping the GitHub Issue as the source of truth for scope, acceptance criteria, ownership, and validation.

## Intended Branch

`docs/member-d-blocker-training`

## Intended Commit Message

`docs(meetings): add member d blocker note training`

## PR Summary Draft

- Adds member d's personal meeting workflow training record.
- Records a safe blocker and next-action example.
- Explains why this training file does not modify shared meeting docs or project workflow rules.

## Validation Command

`just docs-build`

## Peer Review Target

Ask member e to peer-check the training record for workflow consistency before reviewer handoff to f.
