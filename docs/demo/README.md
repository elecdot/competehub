# Demo Runbooks

Demo runbooks are executable acceptance guides for release-sprint and course
inspection workflows.

They sit below the project-wide [Testing Model](../testing.md). The testing
model owns validation layers and evidence principles; this directory owns
concrete demo scripts, example seed data, and per-issue execution guidance.

## Documents

- [Day 1 Acceptance](day1-acceptance.md): Day 1 release-sprint acceptance
  checklist, canonical example seed, and PR/issue evidence addendum.

## Conventions

- Keep runbooks tied to a specific sprint, inspection, or demo path.
- Use canonical example seed data when a real seed CLI does not exist yet.
- Do not make runbooks replace GitHub issue acceptance criteria.
- Update `mkdocs.yml` when adding, removing, or renaming demo pages.
