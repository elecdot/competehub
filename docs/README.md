# Documentation

This directory contains product, technical, setup, and engineering convention documents for CompeteHub, a student-centered competition discovery and recommendation system.

## Start Here

- [Setup](./setup.md): prepare the local workspace and run the applications.
- [Roadmap](./roadmap.md): understand the product and engineering delivery route.
- [Project Workflow](./project_workflow.md): understand how requirements move through issues, PRs, validation, and documentation.
- [Architecture](./architecture.md): understand the system boundaries, runtime components, and data flow.
- [Architecture Decisions](./adr/README.md): review decisions, tradeoffs, and superseded choices.
- [API Spec](./api_spec.md): review the REST API contract and endpoint plan.
- [Data Model](./data_model.md): review the core entities, relationships, and lifecycle rules.
- [Testing Model](./testing.md): understand test layers, manual acceptance, and non-functional validation.
- [Tooling](./tooling.md): find the repository commands for development, checks, and documentation.
- [Agent Guidelines](./agents/README.md): review coding-agent workflow guidance.

## Repository Areas

- `apps/api/`: Flask backend API.
- `apps/web/`: Vue frontend application.
- `docs/`: product and technical documentation.
- `infra/`: local infrastructure definitions.
- `docs/reports/`: course-style reports and analysis artifacts.
- `scripts/`: repository helper scripts.

## Documents

- `PRD.zh.md`: Product requirements and stable business boundaries.
- `roadmap.md`: Product and engineering delivery route.
- `project_workflow.md`: Project delivery workflow and source-of-truth ownership matrix.
- `architecture.md`: High-level system architecture, runtime components, and data flow.
- `api_spec.md`: REST API contract, response envelope, auth boundaries, and endpoint plan.
- `data_model.md`: Core data model, relationships, states, and migration rules.
- `testing.md`: Test strategy, manual acceptance path, and non-functional validation model.
- `demo/`: Demo runbooks, including Day 1 acceptance, canonical example seed,
  and validation evidence format.
- `tech_spec.zh.md`: Technical architecture and implementation design.
- `CONVENTIONS.md`: Repository naming and path conventions.
- `setup.md`: Contributor setup guide.
- `tooling.md`: Development tooling guide.
- `prds/features/`: Single-feature PRDs and the Feature PRD template.
- `agents/`: Coding-agent workflow guidance and task-specific development procedures.
- `adr/`: Architecture decision records for time-bound decisions and tradeoffs.

Related course reports live in `docs/reports/`, including module split and responsibility documents.
The current formal course reports are `docs/reports/01_项目开发计划.md`,
`docs/reports/02_需求规格说明.md`, and `docs/reports/03_软件设计说明.md`.

## Local Conventions

- Use repository-relative paths in documentation.
- Keep long-lived product and architecture decisions in `docs/`.
- Put stage-specific architecture decisions, alternatives, and superseded choices in `docs/adr/`.
- Keep `CONTEXT.md` as glossary-only; do not move ADR rationale or roadmap scope into it.
- Keep `docs/PRD.zh.md` as the stable total PRD; put single-feature PRDs under `docs/prds/features/`.
- Put course-style reports and generated analysis artifacts in `docs/reports/`.
- Use `just docs-build` to validate the MkDocs Material site before changing documentation navigation.
- Keep `mkdocs.yml` synchronized when adding, removing, or renaming documentation pages.
- When a semantic documentation area grows large, create a subdirectory with its own `README.md`.

## Plan

The following documents should be added when their corresponding implementation work becomes concrete:

- `security.md`: auth model, Cookie/session rules, RBAC policy, privacy fields, and audit requirements.
- `deployment.md`: deployment topology, environment variables, release steps, and rollback expectations.
- `observability.md`: logging, metrics, tracing, alerting, and operational dashboards.

Planning notes:

- Do not add speculative operational documents before the project has the relevant runtime surface.
- Prefer updating existing stable documents when the change is a refinement, and create an ADR when the change records a tradeoff or replaceable decision.
- Keep task-level details in implementation issues or local README files, not in stable docs.
