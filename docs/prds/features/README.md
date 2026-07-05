# Feature PRDs

This directory contains single-feature PRDs for CompeteHub.

Feature PRDs are not the stable total PRD. `docs/PRD.zh.md` owns the product
boundary; files in this directory clarify one feature or delivery slice.

## Rules

- Use `template.md` for new Feature PRDs.
- Name files with lowercase English words and hyphens, for example
  `student-profile.md`.
- Link the roadmap phase and source documents checked.
- Include out-of-scope items to prevent scope creep.
- Include testable acceptance criteria.
- Include affected surfaces and validation plan.
- Do not overwrite `docs/PRD.zh.md` through `to-prd`; use this directory unless
  the stable product boundary is explicitly changing.

## Workflow

1. Confirm the feature belongs to the current roadmap phase or intentionally
defer it.
2. Draft the Feature PRD from `template.md`.
3. Review alignment with `docs/PRD.zh.md`, `docs/roadmap.md`,
   `docs/data_model.md`, `docs/api_spec.md`, and `docs/tech_spec.zh.md`.
4. Split implementation into GitHub Issues as vertical slices.
5. Keep the Feature PRD updated when the accepted behavior changes.
