# Documentation

This directory contains product, technical, setup, and engineering convention documents.

## Documents

- `PRD.zh.md`: Product requirements and stable business boundaries.
- `architecture.md`: High-level system architecture, runtime components, and data flow.
- `api_spec.md`: REST API contract, response envelope, auth boundaries, and endpoint plan.
- `data_model.md`: Core data model, relationships, states, and migration rules.
- `tech_spec.zh.md`: Technical architecture and implementation design.
- `CONVENTIONS.md`: Repository naming and path conventions.
- `setup.md`: Contributor setup guide.
- `tooling.md`: Development tooling guide.
- `adr/`: Architecture decision records for time-bound decisions and tradeoffs.

Related course reports live in `reports/`, including module split and responsibility documents.

## Local Conventions

- Use repository-relative paths in documentation.
- Keep long-lived product and architecture decisions in `docs/`.
- Put stage-specific architecture decisions, alternatives, and superseded choices in `docs/adr/`.
- Put course-style reports and generated analysis artifacts in `reports/`.
- When a semantic documentation area grows large, create a subdirectory with its own `README.md`.

## Plan

The following documents should be added when their corresponding implementation work becomes concrete:

- `testing.md`: test strategy, fixtures, coverage expectations, and CI verification commands.
- `security.md`: auth model, Cookie/session rules, RBAC policy, privacy fields, and audit requirements.
- `deployment.md`: deployment topology, environment variables, release steps, and rollback expectations.
- `observability.md`: logging, metrics, tracing, alerting, and operational dashboards.

Planning notes:

- Do not add speculative operational documents before the project has the relevant runtime surface.
- Prefer updating existing stable documents when the change is a refinement, and create an ADR when the change records a tradeoff or replaceable decision.
- Keep task-level details in implementation issues or local README files, not in stable docs.
