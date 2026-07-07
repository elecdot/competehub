# ADR 0008: Ant Design Vue UI Library

## Status

Accepted

## Context

CompeteHub has both student-facing discovery workflows and administrator-facing management workflows. The administrator side depends heavily on tables, filters, forms, review actions, status labels, drawers, dialogs, and configuration pages, so leaving the UI library open would slow implementation and invite inconsistent component choices.

## Decision

Use Ant Design Vue as the frontend UI component library for the current implementation. Shared buttons, forms, tables, modals, drawers, tags, messages, and other common controls should use Ant Design Vue instead of mixing Element Plus, Naive UI, Arco, or ad hoc duplicate component systems.

## Consequences

The management UI can use a component set that fits the project's review, configuration, and audit screens. Student-facing pages must still be styled as a discovery experience rather than a dense back-office surface. Adding the dependency and any theme setup belongs to the implementation PR that first uses the library, and `apps/web/README.md` owns local usage rules.
