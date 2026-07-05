# Domain Docs

This repo uses a single-context domain-doc layout.

## Read Before Domain Work

Before changing product behavior, architecture, implementation plans, reports,
or domain-heavy code, read:

- `CONTEXT.md`
- `docs/roadmap.md`
- relevant ADRs under `docs/adr/`

Use `CONTEXT.md` as glossary-only. Put decision rationale, rejected
alternatives, and consequences in ADRs.

## Layout

```text
/
|-- CONTEXT.md
`-- docs/
    `-- adr/
```

There is no root `CONTEXT-MAP.md`; engineering skills should not look for
per-context `CONTEXT.md` files unless this layout changes.

## Vocabulary

Use the canonical terms from `CONTEXT.md` in issue titles, PRDs, tests, docs,
and implementation notes. If a needed concept is missing or conflicts with
current wording, use `domain-modeling` before inventing new durable terminology.

## ADR Conflicts

If a proposed change contradicts an existing ADR, surface the conflict
explicitly instead of silently overriding it.
