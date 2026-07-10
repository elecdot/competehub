# ADR 0024: Gate Public Registration on Real Verification Delivery

## Status

Accepted

## Context

The typed identity model supports student number, email, and phone identities,
but treating all three as P1 self-registration methods would require external
delivery or institution identity systems. Email needs a working SMTP or
equivalent sender, phone verification normally needs a paid SMS provider, and
knowing a student number does not prove ownership. A course deployment may not
have any of these external services, but silently accepting unverified
identities or exposing test codes would create a misleading and unsafe product
contract.

## Decision

Separate identity-type support from enabled registration capabilities. P1
public registration supports only email and only when a real, vendor-neutral
email sender is configured. Registration creates a `pending_activation` account
and pending email identity, sends a single-use limited-lifetime code, and does
not create a session. Successful verification atomically marks the identity
verified and the account active; the student then logs in normally.

Phone/SMS registration is deferred. Student-number identities come from the
deployment institution's roster, controlled invitation, or administrative
provisioning path and cannot be established merely by self-asserting a student
number. Administrator accounts are also provisioned through a controlled path
and are never publicly registered.

When no real email sender is configured, the frontend hides public registration
and the API reports that registration is unavailable. If production
configuration claims email registration is enabled without a sender, startup
fails. Tests may inject an in-memory sender, and acceptance data may seed an
explicitly verified active account, but production responses and logs never
contain verification codes.

Verification challenges are random, single-use, time-limited, attempt-limited,
and stored only as hashes. Registration and resend responses are generic so
they cannot be used to enumerate existing identities.

## Consequences

The P1 demo and deployments without mail infrastructure remain usable through
controlled pre-provisioned accounts and do not depend on a third-party SaaS.
Deployments that configure SMTP can enable real email self-registration without
changing the account model. SMS and institution SSO remain incremental adapters
rather than prerequisites, while the application never represents an
unverified identity as an active account.
