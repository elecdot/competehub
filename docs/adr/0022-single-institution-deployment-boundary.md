# ADR 0022: Single-Institution Deployment Boundary

## Status

Accepted

## Context

The initial user model made student numbers globally unique and stored college
without an institution. Admin permissions, dictionaries, and school-level value
notes also lacked a tenant key. Leaving this implicit could make the product
appear ready for a shared multi-university platform without the required tenant
isolation and governance model.

## Decision

P1 is one deployment owned by one部署高校. Student-number uniqueness, colleges,
administrators, major and grade dictionaries, school-level recognition, and
governance all operate inside that deployment boundary. The host institution is
a required deployment configuration fact rather than a user-selected profile
string.

The competition catalog may include national competitions and trustworthy
notices or official sources outside the host institution. Source origin does not
change user tenancy. A future shared multi-institution platform requires a new
decision covering institution entities, tenant-scoped uniqueness, authorization,
configuration, data access, and operations.

## Consequences

P1 needs no tenant key on every business row. Student number remains unique in
one deployment, and `college` means a college within the configured host
institution. Documentation and UI must not describe the current product as a
multi-tenant university platform.
