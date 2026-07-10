# Web App

This directory contains the Vue frontend application for CompeteHub.

## Responsibilities

- Own the student and admin browser experiences.
- Call the backend through `/api/v1` REST APIs.
- Keep route, store, and UI state conventions close to the frontend source.

This directory does not own backend business rules, database models, infrastructure, or course reports.

## Structure

- `src/api/`: HTTP client and API wrappers.
- `src/components/`: Reusable UI components.
- `src/layouts/`: Page shells and navigation layouts.
- `src/pages/`: Route-level views.
- `src/router/`: Vue Router setup.
- `src/stores/`: Pinia stores.
- `src/types/`: Shared TypeScript types.
- `src/utils/`: Frontend-only helpers.

## Local Commands

Run from the repository root:

```bash
just web-install
just web-dev
just web-build
just web-lint
```

Or run npm directly:

```bash
npm --prefix apps/web install
npm --prefix apps/web run dev
```

## Local Conventions

- Route-level components belong in `src/pages/`.
- Reusable state belongs in Pinia stores, not ad hoc module globals.
- Frontend permission checks are for UX only; backend APIs must enforce authorization.
- Ant Design Vue is the installed UI component library; see
  `docs/adr/0008-ant-design-vue-ui-library.md`. Import components locally in
  Vue files so production builds can tree-shake unused controls.
- Do not mix Element Plus, Naive UI, Arco, or another general-purpose UI component library into the same app without a superseding ADR.
- Shared buttons, forms, tables, modals, drawers, tags, messages, and management
  controls should use Ant Design Vue.
- Vite proxies `/api` to the Flask backend during local development.
- User-facing competition dates use the `Asia/Shanghai` product calendar time
  zone; API timestamps remain timezone-aware UTC instants.

## Quality Gates

- Current lint gate: `just web-lint`, which runs `vue-tsc --noEmit`.
- Current build gate: `just web-build`, which runs type checking and Vite build.
- Later stages add ESLint with `eslint-plugin-vue`, Prettier, Vitest with Vue Test Utils, and Playwright according to `docs/adr/0010-staged-frontend-quality-gates.md`.
- Any PR that introduces a new frontend quality tool must update `apps/web/package.json`, `package-lock.json`, the root `justfile`, and the relevant docs together.
