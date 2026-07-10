# ADR 0023: Model Typed User Identities

## Status

Accepted

## Context

The initial user table stored nullable email, phone, and student number columns,
while login searched one untyped value across all three. It therefore allowed
one user's email text to equal another user's student number and attempted to
disambiguate the account by password. The model also lacked one normalization
boundary for uniqueness and future identity verification.

## Decision

Separate the user account subject from typed `user_identities`. An identity has
`identity_type`, normalized value, display value, verification state, and owner.
P1 types are `student_no`, `email`, and `phone`. A user may bind multiple
identities, and uniqueness is enforced by type plus normalized value inside the
single deployment boundary.

Login explicitly submits identity type and identifier. Email is trimmed and
case-normalized, phone is normalized to E.164, and student number is Unicode
normalized and trimmed while preserving leading zeroes and following the
deployment institution's format policy. Authentication errors do not disclose
whether the normalized identity exists.

## Consequences

The user table retains account id, password credential, display name, role, and
status rather than three identity columns. Registration/login schemas and UI
use an explicit identity selector. `/me` returns account facts without exposing
sensitive bound identifiers. Cross-field matching and password-based account
selection are removed.
