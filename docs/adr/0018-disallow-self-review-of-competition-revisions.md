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

Keep `admin` as the formal product role and grant赛事编辑权限, 赛事审核权限, and
赛事维护权限 as independent administrator capabilities. One account may hold
multiple capabilities, but the reviewer of a submitted revision must differ
from that revision's submitter. 赛事维护权限 authorizes cancellation, expiry,
archival, and emergency offline with a reason; it does not authorize revision
editing or approval, and restoration still requires an independently reviewed
corrected revision. Backend authorization enforces these boundaries from
persisted revision, review, and capability facts.

An editor may withdraw an unreviewed submission back to an editable draft.
Approve, reject, and return actions require another administrator account with
review permission. P1 has no silent self-review or default bypass. Any future
emergency override requires a separate decision and strong audit evidence.

## Consequences

Review records need the target revision, submitter, and reviewer identity.
Admin provisioning and Day 1 seed data need distinct editor and reviewer
accounts. The canonical editor also holds `recommendation_editor`; the canonical
reviewer holds competition review and maintenance plus
`recommendation_reviewer`, so P1/P2 acceptance remains executable with two
admins. Tests must reject self-review independently of frontend controls.
