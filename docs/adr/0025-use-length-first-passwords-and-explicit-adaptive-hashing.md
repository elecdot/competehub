# ADR 0025: Use Length-First Passwords and Explicit Adaptive Hashing

## Status

Accepted

## Context

The first authentication slice accepted any non-empty password and delegated
hash selection to framework defaults. That makes a one-character password a
valid product behavior and allows dependency upgrades to change password work
factors without an explicit project decision. Traditional composition and
periodic-rotation rules would add user friction without addressing common or
compromised passwords.

## Decision

P1 treats passwords as a single authentication factor. User-chosen passwords
contain at least 15 and at most 128 Unicode code points after NFC normalization.
All supported characters, including spaces, are accepted; paste, browser
autofill, and password managers are supported. Passwords are processed in full,
are never silently truncated, and have no upper/lower-case, number, or symbol
composition requirement.

New passwords are compared in full with a repository-managed local blocklist of
common or compromised passwords and obvious context-specific values derived
from the product or account identity. The runtime does not need an online breach
lookup service. Password changes are required when compromise is known or as an
explicit security action, not on an arbitrary schedule.

Password storage uses an adaptive one-way hash with algorithm and work
parameters encoded in the stored hash. Argon2id is preferred. If it is not
available, scrypt may be used only with explicit parameters meeting the current
OWASP baseline and benchmarked for the deployment. Framework defaults are not a
security contract.

Failed logins use the same public response for unknown, incorrect-password,
pending, and disabled accounts. Attempts are progressively rate-limited by both
normalized typed-identity key and request source. Remote failures do not create
a permanent account lock that an attacker could use for denial of service.

## Consequences

The policy supports memorable passphrases and password managers without an
external service or arbitrary character puzzles. Implementation must add a
local blocklist, explicit hash configuration, rate limiting, and boundary tests.
Existing test and seed credentials must be updated when the implementation
changes, and any future algorithm migration must preserve verification of old
hashes while rehashing successful logins as needed.
