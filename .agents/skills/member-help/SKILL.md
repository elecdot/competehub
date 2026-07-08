---
name: member-help
description: Help a CompeteHub member regain enough context to continue assigned work.
disable-model-invocation: true
---

# Member Help

Member Help is a user-invoked, read-only help-forward skill. Use it only when a
collaborator explicitly asks for `/member-help`.

The goal is not to diagnose once and stop. The goal is to help the agent and
member share enough context to continue assigned project work.

## 1. Identify

Confirm the member, assigned work, current intent, and blocker.

Prefer member-provided assignment context:

- member id: a-f
- assigned issue or PR
- daily standup owner list excerpt
- current blocker or question

If the member only provides identity and no assigned work, ask for the standing
meeting issue or owner list. If that is unavailable, proceed with
assignment-recovery and state that the result is only a candidate, not a new
assignment.

Completion criterion: member identity and assignment source are known, or the
missing assignment is explicitly marked as recovery.

## 2. Index

Use the current conversation context when it is sufficient. Do not re-index just
because this step exists.

If context is insufficient, run a lightweight index pass. Read metadata first,
not full issue bodies, comments, PR diffs, or CI logs.

Useful index fields:

- issue/PR number, title, labels, assignee, updated time, URL
- roadmap phase, area, module, Delivery Ownership summary
- PR draft/ready state, review state, linked issue, changed filenames

Completion criterion: the likely issue/PR/docs candidates are narrowed to the
smallest useful set.

## 3. Hydrate

Deep-read only what is needed for the member's next step.

Default hydrate set:

- the assigned issue or PR
- at most one linked issue or PR
- the most relevant project docs for the question

Read comments, diffs, review threads, or CI logs only for review/debug/blocker
work.

Completion criterion: the agent can explain the assigned work, relevant
constraints, and next action without guessing.

## 4. Help Forward

Continue the member toward work. Do not produce a long diagnostic report by
default.

Common help-forward outcomes:

- explain the assigned issue in plain language
- identify the next concrete action
- give the smallest Git/PR/validation path needed now
- provide one reusable prompt for the member to continue
- recommend switching to `delivery-slice`, `tdd`, review, or another workflow

If the member explicitly asks the agent to implement, edit, commit, create an
issue, open a PR, or perform external writes, stop Member Help and switch to the
appropriate project workflow. Follow `AGENTS.md` and preview required writes.

Completion criterion: the member and agent have enough shared context to keep
working in the current conversation or enter a concrete workflow.

## Reference

Read `references/patterns.md` only when a concrete help pattern or reusable
member prompt would improve the response.
