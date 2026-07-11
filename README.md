# CompeteHub

CompeteHub（大学生竞赛信息智能筛选与推荐系统）is a
student-centered system for discovering, following, and recommending 赛事.

Students maintain a profile, search and filter 赛事, inspect details, 收藏 or
订阅 relevant 赛事, and follow key time nodes through 站内提醒 and a
个人赛事日历. Administrators create 赛事 records from 可信来源 through 人工录入,
review and publish trustworthy 赛事 information, maintain states, and support
operations through configuration, audit, and statistics.

This is a course project with a small team and a short delivery window, so the
repository keeps product documents, technical documents, course reports,
validation commands, and workflow guidance close to the code.

## Product Scope

Implementation follows the roadmap phases in [docs/roadmap.md](./docs/roadmap.md).
This table summarizes the product scope without claiming every item is already
implemented.

| Area | Roadmap scope |
| --- | --- |
| Student workflow | Registration/login, profile maintenance, public 赛事 search/filter/detail, 收藏, 订阅, 站内提醒, and 个人赛事日历. |
| Admin workflow | 人工录入 from 可信来源, review publication, and 赛事 state maintenance. |
| Recommendations | 规则推荐 and 推荐理由, with explainable configuration work in P2. |
| Operations | User management, configuration, audit logs, and basic statistics for governance and maintainability. |
| Documentation | Product, roadmap, architecture, API, data model, testing, setup, and course reports under `docs/`. |

## Current Delivery

The project is moving from a reliable runnable skeleton toward the P1 核心闭环:

- P0 establishes the local development loop: PostgreSQL, Redis, Flask API, Vue
  app, health checks, root `just` commands, and CI-aligned local checks.
- P1 proves the core product value: administrators publish trustworthy 赛事
  data, and students discover, inspect, subscribe to, and track relevant 赛事.
- P2 and later phases add recommendation depth, governance, hardening, and
  optional extensions after the core loop is stable.

Daily implementation state belongs in GitHub Issues and PRs. Lightweight
coordination notes live under [docs/meetings/](./docs/meetings/).

## System Shape

- Frontend: Vue application in [apps/web](./apps/web/).
- Backend: Flask API in [apps/api](./apps/api/).
- Data and infrastructure: PostgreSQL and Redis through
  [infra/docker-compose.yml](./infra/docker-compose.yml).
- Documentation site: MkDocs Material configured by [mkdocs.yml](./mkdocs.yml).
- Commands: the root [justfile](./justfile) provides setup, development,
  validation, build, documentation, and infrastructure checks.

## Quick Start

For detailed setup notes, see [docs/setup.md](./docs/setup.md) and
[docs/tooling.md](./docs/tooling.md).

Prerequisites:

- `git`
- `just`
- `uv`
- Node.js and npm
- Docker Desktop with WSL integration enabled when using local PostgreSQL and
  Redis

Install dependencies:

```bash
just setup
```

Create a local environment file if one does not already exist:

```bash
cp .env.example .env
```

Start local PostgreSQL and Redis:

```bash
just infra-up
```

Start the backend and frontend in separate terminals:

```bash
just api-dev
just web-dev
```

By default, the frontend dev server proxies `/api` requests to the Flask API on
`localhost:5000`.

## Validation

Use the broad local gate when preparing a release-like handoff:

```bash
just check
```

Use targeted checks while working:

```bash
just doctor
just api-test
just api-lint
just api-format
just web-lint
just web-build
just web-e2e
just docs-build
just infra-config
```

## Working In This Repo

- Human contributors should start with [CONTRIBUTING.md](./CONTRIBUTING.md).
- Coding agents must follow [AGENTS.md](./AGENTS.md).
- Delivery work follows [docs/project_workflow.md](./docs/project_workflow.md):
  Roadmap -> Feature PRD -> Issue -> Design Impact -> Code/Test -> PR -> Docs.
- Git conventions live in [README-GIT.md](./README-GIT.md).
- GitHub Issues and PRs are the source of truth for implementation state;
  meeting notes under `docs/meetings/` are lightweight coordination records.

## Documentation Map

| Need | Start here |
| --- | --- |
| Canonical project language | [CONTEXT.md](./CONTEXT.md) |
| Product boundary | [docs/PRD.zh.md](./docs/PRD.zh.md) |
| Delivery sequence | [docs/roadmap.md](./docs/roadmap.md) |
| Project workflow | [docs/project_workflow.md](./docs/project_workflow.md) |
| Architecture | [docs/architecture.md](./docs/architecture.md) |
| API contract | [docs/api_spec.md](./docs/api_spec.md) |
| Data model | [docs/data_model.md](./docs/data_model.md) |
| Testing model | [docs/testing.md](./docs/testing.md) |
| Setup and tooling | [docs/setup.md](./docs/setup.md), [docs/tooling.md](./docs/tooling.md) |
| Course reports | [docs/reports/](./docs/reports/) |
| Application packages | [apps/README.md](./apps/README.md) |
| Local infrastructure | [infra/README.md](./infra/README.md) |
| Full documentation site | [mkdocs.yml](./mkdocs.yml), `just docs-serve` |
