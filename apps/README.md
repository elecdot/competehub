# Applications

This directory contains deployable application packages.

## Structure

- `api/`: Flask backend API.
- `web/`: Vue frontend application.

## Common Workflows

Run from the repository root:

```bash
just api-dev
just web-dev
```

Use `just --list` to see all available app, infrastructure, and quality-check commands.

## Local Conventions

- Each application directory must include its own `README.md`.
- Shared runtime assumptions should be documented here; app-specific commands belong in the app-level README.
- Do not place course reports, product documents, or infrastructure files in this directory.
