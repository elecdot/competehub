# ADR 0018: Disallow Self-Review Of Competition Revisions

## Status

Accepted

## Context

The initial publication flow allowed one administrator account to create,
submit, and approve the same赛事届次. That is convenient for a demo but makes the
trusted-source review claim a self-attestation. Creating separate editor and
reviewer user roles would add role complexity even though team members may need
to perform both duties on different records.

## Decision

Keep `admin` as the formal product role and grant赛事编辑权限 and赛事审核权限 as
administrator capabilities. One account may hold both capabilities, but the
reviewer of a submitted revision must differ from that revision's submitter.
Backend authorization enforces this separation from persisted revision and
review facts.

An editor may withdraw an unreviewed submission back to an editable draft.
Approve, reject, and return actions require another administrator account with
review permission. P1 has no silent self-review or default bypass. Any future
emergency override requires a separate decision and strong audit evidence.

## Consequences

Review records need the target revision, submitter, and reviewer identity.
Admin provisioning and Day 1 seed data need distinct editor and reviewer
accounts even when each person has both capabilities for other work. Tests must
reject self-review independently of frontend controls.
