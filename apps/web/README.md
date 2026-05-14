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
npm --prefix apps/web install
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
- UI component library adoption requires an ADR and this README must be updated with usage rules.
- Vite proxies `/api` to the Flask backend during local development.
