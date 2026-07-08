# Feature PRD Agent Workflow

Feature PRDs for CompeteHub are durable project documents, not GitHub issues.
Use this workflow when an agent drafts a new feature requirement, especially
when a personal helper such as `to-prd` is used as synthesis input.

## Rules

- Create or update `docs/prds/features/*.md`; do not publish the PRD itself as
  a GitHub issue.
- Use `docs/prds/features/template.md` for the final artifact.
- Keep `docs/PRD.zh.md` unchanged unless the user explicitly asks to change the
  stable product boundary.
- Mark new PRDs as `Draft` unless the user explicitly confirms `Reviewed` or
  `Accepted`.
- Record uncertain scope, ownership, tests, or product behavior under
  `Risks And Open Questions`; do not silently promote guesses into accepted
  requirements.
- Preview durable document changes before writing or replacing a Feature PRD.
- Do not apply `ready-for-agent` to a PRD. That label belongs to implementation
  issues after the PRD is split into vertical slices and issue ownership is
  complete.

## Required Context

Before drafting or updating a Feature PRD, read:

- `docs/prds/features/template.md`
- `docs/prds/features/README.md`
- `docs/project_workflow.md`
- `docs/roadmap.md`
- `CONTEXT.md`
- `docs/PRD.zh.md`

Read `docs/api_spec.md`, `docs/data_model.md`, `docs/architecture.md`,
`docs/tech_spec.zh.md`, and relevant reports when the feature affects those
surfaces.

## Mapping Generic PRD Drafts

If `to-prd` or another generic PRD helper produces a draft, map it into the
local template instead of preserving the generic template shape:

| Generic section | Local destination |
|---|---|
| Problem Statement | `Background And Goal` |
| Solution | `Functional Requirements`, `Non-Functional Requirements`, and `Impact Surface` |
| User Stories | `User Stories` |
| Implementation Decisions | `Impact Surface`, plus owning architecture/API/data docs when needed |
| Testing Decisions | `Validation Plan` |
| Out of Scope | `Out Of Scope` |
| Further Notes | `Risks And Open Questions` |

The local template must still include status, roadmap phase, owner, related
issues, source documents checked, acceptance criteria, impact surface, and
validation plan.

## Handoff To Issues

After a Feature PRD is reviewed or accepted, split implementation through the
issue workflow:

1. Use vertical slices rather than horizontal layer-only tasks.
2. Link the Feature PRD from each implementation issue.
3. Fill Delivery Ownership according to `docs/project_workflow.md`.
4. Apply `ready-for-agent` only when the issue has complete scope, acceptance
   criteria, validation plan, and Delivery Ownership.
