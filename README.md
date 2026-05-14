# CompeteHub

CompeteHub is a student-centered competition discovery and recommendation system.

The repository now contains the initial Vue frontend, Flask backend, Redis/PostgreSQL local infrastructure, and product/technical documentation.

## Quick Start

>[!tip] See [setup.md](./docs/setup.md) for more comprehensive setup guide.

Prerequisites:

- `just`
- `uv`
- Node.js and npm
- Docker Desktop with WSL integration enabled when running local infrastructure

```bash
# Install backend dependencies.
just api-sync

# Install frontend dependencies.
npm --prefix apps/web install

# Start local PostgreSQL and Redis.
just infra-up

# Start backend and frontend in separate terminals.
just api-dev
just web-dev
```

Useful checks:

```bash
just api-test
just api-lint
just web-lint
just web-build
docker compose -f infra/docker-compose.yml config
```

## Documentation

`/`:
- [README-GIT.md](README-GIT.md): Git workflow and commit guidelines for contributors and coding agents.

`apps/`:
- [README.md](./apps/README.md): Application directory overview and local conventions.
- [api/README.md](./apps/api/README.md): Backend API overview and local conventions.
- [web/README.md](./apps/web/README.md): Frontend app overview and local conventions.

`docs/`:
- [README.md](./docs/README.md): Documentation directory overview and local conventions.
- [PRD.md](./docs/PRD.md): Product requirements and stable business boundaries.
- [architecture.md](./docs/architecture.md): High-level system architecture and data flow.
- [api_spec.md](./docs/api_spec.md): REST API contract and endpoint plan.
- [data_model.md](./docs/data_model.md): Core data model, relationships, and state rules.
- [tech_spec.md](./docs/tech_spec.md): Technical architecture and implementation design.
- [adr/README.md](./docs/adr/README.md): Architecture decision records and ADR conventions.
- [CONVENTIONS.md](./docs/CONVENTIONS.md): Repository naming and file organization conventions.
- [setup.md](./docs/setup.md): A quick setup guideline for developers.
- [tooling.md](./docs/tooling.md): Development tools and their usage.

`reports/`:
- [README.md](./reports/README.md): Report directory overview and local conventions.
- [requirements.md](./reports/requirements.md): Requirement-gathering and initial requirement analysis report.
- [module_breakdown.md](./reports/module_breakdown.md): Module split, interfaces, and member responsibilities for course work.

`infra/`:
- [README.md](./infra/README.md): Local infrastructure overview and conventions.

`scripts/`:
- [README.md](./scripts/README.md): Repository helper scripts and agent-safe command conventions.

## Open Loops

- [x] Complete the requirements analysis report
- [x] Complete module split and responsibility report
- [x] Decide how to structure the frontend and backend files and organize the technology stack
- [x] Initialize agent-safe command wrapper
