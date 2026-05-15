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
just docs-build
docker compose -f infra/docker-compose.yml config
```

## Documentation

`/`:
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
- [architecture.md](./docs/architecture.md): High-level system architecture and data flow.
- [api_spec.md](./docs/api_spec.md): REST API contract and endpoint plan.
- [data_model.md](./docs/data_model.md): Core data model, relationships, and state rules.
- [tech_spec.zh.md](./docs/tech_spec.zh.md): Technical architecture and implementation design.
- [adr/README.md](./docs/adr/README.md): Architecture decision records and ADR conventions.
- [CONVENTIONS.md](./docs/CONVENTIONS.md): Repository naming and file organization conventions.
- [setup.md](./docs/setup.md): A quick setup guideline for developers.
- [tooling.md](./docs/tooling.md): Development tools and their usage.

`reports/`:
- [README.md](./reports/README.md): Report directory overview and local conventions.
- [requirements.md](./reports/requirements.md): Requirement-gathering and initial requirement analysis report.
- [module_breakdown_v1.0.md](./reports/module_breakdown_v1.0.md): Module split, interfaces, and member responsibilities for course work.

`infra/`:
- [README.md](./infra/README.md): Local infrastructure overview and conventions.

`scripts/`:
- [README.md](./scripts/README.md): Repository helper scripts and agent-safe command conventions.

The MkDocs Material site is configured by [mkdocs.yml](./mkdocs.yml). Use `just docs-serve` for local preview and `just docs-build` for strict validation.

## Open Loops

- [ ] Maybe make project Windows-native compatible: use Huey instead of Celery;
use cross-platform compatible scripts (maybe use Python? idk yet); write AGENTS.md.
NOTE: I considering encapsulate every service using Docker: for the performance
reason, I do not done this yet. But I think we finally need it tho.
- [ ] Maybe ask for TODO tags from agents? (Maybe ask for clarify and evidence is better?)
- [ ] Ask AI follow .editorconfig? (seems Agent would not do it by itself, but probably because it can't?)
- [ ] Move report into docs/reports, leave reports/ empty for further work.
- [ ] Make agent-env.sh general (instead of only for uv)
```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle
    "F",   # pyflakes
    "I",   # isort
    "UP",  # pyupgrade
    "B",   # bugbear
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```
