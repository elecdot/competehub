# ADR 0010: Staged Frontend Quality Gates

## Status

Accepted; E2E timing amended by ADR 0031

## Context

The Vue app currently has Vite, TypeScript, Vue Router, Pinia, Axios, and `vue-tsc`-based checks. Adding all frontend lint, format, unit, component, and end-to-end tooling before pages and stores stabilize would create dependency and maintenance cost before there is enough UI surface to test meaningfully. At the same time, the project needs a clear testing direction for the course inspection and later implementation issues.

## Decision

Adopt frontend quality gates in stages. The immediate gate remains `vue-tsc --noEmit` through `just web-lint`, plus `just web-build`. After P1 pages and stores stabilize, add ESLint with `eslint-plugin-vue` and Prettier. After the core components and stores stabilize, add Vitest and Vue Test Utils for stores, filters, detail states, and message states.

ADR 0031 now requires Playwright when the P1 administrator governance workbench
is completed, beginning with distinct editor/reviewer publication to student
visibility. Component-test staging and incremental expansion of the E2E path
remain unchanged.

## Consequences

This decision records the tool direction without installing dependencies in the technical-decision PR. Each tooling stage must update `apps/web/package.json`, the lockfile, `justfile`, and the relevant docs in the same change that introduces the tool. Until then, frontend implementation PRs should run the existing static and build checks and use manual acceptance where no test harness exists.
