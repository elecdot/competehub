# GitHub Configuration

This directory contains GitHub-hosted automation and repository metadata.

## Responsibilities

- Own GitHub Actions workflows and related repository automation.
- Keep CI behavior discoverable from the repository root.
- Avoid storing product, architecture, or course-report content here.

## Structure

- `workflows/`: GitHub Actions workflow definitions.

## Local Conventions

- Use lowercase workflow file names with `.yml`.
- Keep each workflow focused on one automation concern.
- Document non-obvious workflow behavior in `workflows/README.md`.
- Prefer existing repository commands from `justfile` or documented package scripts when defining CI steps.
