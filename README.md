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

You can install tool versions manually or use `mise` with the checked-in
`mise.toml`.

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
just docs-build
docker compose -f infra/docker-compose.yml config
```

## Documentation

`/`:
- [CONTEXT.md](CONTEXT.md): Canonical project language and domain terms.
- [README-GIT.md](README-GIT.md): Git workflow and commit guidelines for contributors and coding agents.

`.github/`:
- [README.github.md](./.github/README.github.md): GitHub automation overview and local conventions.
- [workflows/README.md](./.github/workflows/README.md): GitHub Actions workflow overview and CI command mapping.

`apps/`:
- [README.md](./apps/README.md): Application directory overview and local conventions.
- [api/README.md](./apps/api/README.md): Backend API overview and local conventions.
- [web/README.md](./apps/web/README.md): Frontend app overview and local conventions.

`docs/`:
- [README.md](./docs/README.md): Documentation directory overview and local conventions.
- [PRD.zh.md](./docs/PRD.zh.md): Product requirements and stable business boundaries.
- [roadmap.md](./docs/roadmap.md): Product and engineering delivery route.
- [architecture.md](./docs/architecture.md): High-level system architecture and data flow.
- [api_spec.md](./docs/api_spec.md): REST API contract and endpoint plan.
- [data_model.md](./docs/data_model.md): Core data model, relationships, and state rules.
- [tech_spec.zh.md](./docs/tech_spec.zh.md): Technical architecture and implementation design.
- [adr/README.md](./docs/adr/README.md): Architecture decision records and ADR conventions.
- [CONVENTIONS.md](./docs/CONVENTIONS.md): Repository naming and file organization conventions.
- [setup.md](./docs/setup.md): A quick setup guideline for developers.
- [tooling.md](./docs/tooling.md): Development tools and their usage.

`docs/reports/`:
- [README.md](./docs/reports/README.md): Report directory overview and local conventions.
- [01_项目开发计划.md](./docs/reports/01_项目开发计划.md): Project development plan formal report.
- [02_需求规格说明.md](./docs/reports/02_需求规格说明.md): Requirements specification formal report.
- [03_软件设计说明.md](./docs/reports/03_软件设计说明.md): Software design specification formal report.
- [requirements.md](./docs/reports/requirements.md): Requirement-gathering and initial requirement analysis report.
- [module_breakdown_v1.0.md](./docs/reports/module_breakdown_v1.0.md): Module split, interfaces, and member responsibilities for course work.

`infra/`:
- [README.md](./infra/README.md): Local infrastructure overview and conventions.

`scripts/`:
- [README.md](./scripts/README.md): Repository helper scripts and agent-safe command conventions.

The MkDocs Material site is configured by [mkdocs.yml](./mkdocs.yml). Use `just docs-serve` for local preview and `just docs-build` for strict validation.

## Roadmap

Development sequencing and remaining product/engineering work are tracked in
[docs/roadmap.md](./docs/roadmap.md). Use it with [CONTEXT.md](./CONTEXT.md)
when aligning requirements, architecture, reports, and implementation tasks.
