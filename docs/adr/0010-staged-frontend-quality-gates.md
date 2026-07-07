# ADR 0010: Staged Frontend Quality Gates

## Status

Accepted

## Context

The Vue app currently has Vite, TypeScript, Vue Router, Pinia, Axios, and `vue-tsc`-based checks. Adding all frontend lint, format, unit, component, and end-to-end tooling before pages and stores stabilize would create dependency and maintenance cost before there is enough UI surface to test meaningfully. At the same time, the project needs a clear testing direction for the course inspection and later implementation issues.

## Decision

Adopt frontend quality gates in stages. The immediate gate remains `vue-tsc --noEmit` through `just web-lint`, plus `just web-build`. After P1 pages and stores stabilize, add ESLint with `eslint-plugin-vue` and Prettier. After the core components and stores stabilize, add Vitest and Vue Test Utils for stores, filters, detail states, and message states. After the main workflow is stable, add Playwright for the administrator publication to student subscription and reminder path.

## Consequences

This decision records the tool direction without installing dependencies in the technical-decision PR. Each tooling stage must update `apps/web/package.json`, the lockfile, `justfile`, and the relevant docs in the same change that introduces the tool. Until then, frontend implementation PRs should run the existing static and build checks and use manual acceptance where no test harness exists.
