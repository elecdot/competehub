---
name: delivery-ops
description: Help the human owner run CompeteHub delivery planning, issue slicing, PR readiness review, merge-readiness analysis, and standup sync.
disable-model-invocation: true
---

# Delivery Ops

Delivery Ops is a user-invoked, prepare-first skill for the human owner's
CompeteHub delivery work. It creates delivery views and previews; it does not
replace product ownership, code review responsibility, or merge authority.

## 1. Reality Check

Start every run with a light reality check.

Read the minimum current context needed for the request:

- Always for non-trivial delivery work: `AGENTS.md`,
  `docs/project_workflow.md`, `docs/roadmap.md`, and `CONTEXT.md`.
- Latest relevant `docs/meetings/` standup record, preferring today's latest
  `YYYY-MM-DD-standup-N.md` when present.
- GitHub issue and PR metadata when available: number, title, state, labels,
  assignee or author, draft/readiness, review decision, updated time, and URL.
- Branch-specific source docs only when needed, such as Feature PRDs, issue
  forms, PR template, API, data model, architecture, or testing docs.

If the user has not provided current reality, read the latest standup first,
then ask one focused grilling-style question only when the missing fact changes
the output:

```text
今天的交付目标和组员现实情况是否沿用最新站会记录？如果不是，请告诉我变更：deadline、可用成员、blocker、必须完成的 demo path。
```

Completion criterion: the response can state the selected branch, roadmap phase,
source documents read and intentionally skipped, current reality assumptions,
missing reality, affected surfaces, external writes needed, and validation plan.

## 2. Route

Choose exactly one primary branch unless the user asks for a combined run:

- No branch specified -> `daily board`.
- Morning, evening, standup, owner list, blocker notes, or meeting notes ->
  `standup sync`.
- Issue slicing, work assignment, task launch, or implementation preview ->
  `issue preview`.
- PR ready, review readiness, acceptance, validation evidence, or risk ->
  `PR readiness`.
- Merge, merge order, squash, approve, release train, or end-of-day merge ->
  `merge queue`.

Use `references/output-formats.md` when producing one of these outputs.

Completion criterion: one branch is named, and downstream skills are named only
when the request should leave Delivery Ops.

## 3. Guard Truth

Use this source-of-truth split:

- GitHub issues and PRs own delivery truth: scope, acceptance, validation,
  ownership, review state, and merge state.
- `docs/meetings/` owns reality notes: focus, owner list, availability,
  blockers, next actions, and actual daily progress.

When they conflict, do not silently choose. Mark `Needs reconciliation`, show
the conflicting facts, and ask the human owner to decide. If a standup mentions
work without an issue, generate an issue preview rather than treating the
standup as the task source.

Completion criterion: every recommendation cites whether it came from GitHub,
meetings, source docs, or user-provided reality.

## 4. Handle Missing Reality

Do not invent delivery facts.

- `daily board`: may proceed with assumptions. Include `Assumptions / Missing
  Reality`.
- `issue preview`: stop for missing deadline, DRI, validation owner, docs
  impact, or acceptance boundary.
- `standup sync`: stop for missing day target or member reality.
- `PR readiness`: proceed from PR facts, but mark product or acceptance gaps as
  `Needs owner decision`.
- `merge queue`: never call a PR ready when validation, review state, risk
  acceptance, or deadline context is missing.

Completion criterion: every unknown that affects assignment, write actions, or
merge readiness is either resolved or explicitly blocks the recommendation.

## 5. Branches

### Daily Board

Produce a concise owner-facing delivery board from roadmap, standup reality, and
GitHub metadata. Prefer current roadmap and demo-critical vertical slices over
issue volume.

Completion criterion: the board separates must-finish, should-finish, blocked
work, review queue, merge candidates, and deferred work.

### Issue Preview

Prepare issue previews only. Link Feature PRDs or source docs when relevant.
Use vertical slices and complete Delivery Ownership before recommending
`ready-for-agent` or `ready-for-human`.

If a feature requirement itself is unclear, route to the Feature PRD workflow
instead of writing implementation issues.

Completion criterion: the preview includes goal, scope, out of scope,
acceptance criteria, affected surfaces, validation plan, Delivery Ownership,
and source links.

### PR Readiness

Check whether a PR is reviewable and aligned before merge. Read PR diff, linked
issue or PRD, validation evidence, docs impact, and review comments only as
needed.

Classify the verdict as `Ready`, `Not ready`, or `Risky`.

Completion criterion: required changes before merge are explicit, and the
suggested review comment is ready for the human owner to paste or adapt.

### Merge Queue

Recommend merge order and squash messages. Do not approve or merge by default.
Only execute approve or squash merge after the user explicitly commands it and
after a final preview of PR number, base/head, checks, remaining risk, and
squash message.

Completion criterion: every merge candidate has clear linked work, sufficient
validation, resolved docs impact, acceptable risk, and a suggested squash
message.

### Standup Sync

Treat standup records as the daily reality view.

- Morning or previous night: preview the day's `Focus` and `Owner List`.
- Evening: preview updates to the same file's status, blockers, next actions,
  notes, and tomorrow carry-over.
- Default to one file per day: `docs/meetings/YYYY-MM-DD-standup-0.md`.
  Use a higher `N` only for special same-day additional records.

Do not turn standup records into a second issue tracker. Scope and acceptance
still belong in GitHub issues and source docs.

Completion criterion: the preview can be applied to one standup file and every
row links back to a GitHub issue or explicitly needs an issue preview.

## 6. Authority

Prepare first. Execute only on explicit command.

Preview and wait for confirmation before creating or editing GitHub issues,
labels, PR bodies, PR comments, issue state, standup files, durable project
documents, commits, pushes, approvals, or merges.

For approve or squash merge, require a second confirmation even after a merge
queue recommendation.

Completion criterion: the final response states what was only recommended,
what was written, and what still needs human confirmation.

## 7. Handoff

Leave Delivery Ops when the request becomes another focused workflow:

- Feature requirement drafting -> Feature PRD workflow.
- Implementation, docs slice, or bug fix -> `delivery-slice`.
- Test-first behavior work -> `tdd`.
- Deep code review -> code review or GitHub review workflow.
- UI behavior testing -> `webapp-testing`.

Completion criterion: the handoff names the target workflow and passes the
current issue, PR, source docs, reality assumptions, and validation expectations.
