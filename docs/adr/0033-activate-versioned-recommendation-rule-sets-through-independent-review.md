# ADR 0033: Activate Versioned Recommendation Rule Sets through Independent Review

## Status

Accepted

## Context

The initial model stored independently mutable recommendation-rule rows, while
the P2 feature PRD allowed service constants for the first tracer. Either form
would make it difficult to identify which behavior produced a result, preview a
coherent candidate, review differences, atomically switch versions, or retain
the prior behavior for audit. Recommendation changes affect every eligible
student and therefore need a bounded governance workflow rather than direct
production edits.

## Decision

Personalized recommendation reads exactly one immutable active
`recommendation_rule_set`. A reproducible seed creates the initial active
version. A rule set owns controlled rule rows with bounded integer weights,
schema-validated structured conditions, reason templates, and enabled state.
Initial rule codes cover major, grade, interest, deadline urgency, and general
fallback. Executable expressions and arbitrary scripts are forbidden.

Drafts are editable. Submission freezes a candidate snapshot for a distinct
`recommendation_reviewer`, who approves and activates, rejects, or returns it
with a comment. The submitter cannot review the same version. Activation and
retirement of the prior active version occur atomically; active, retired, and
decided versions remain immutable. Continued work clones a successor draft.

The workbench provides version history, controlled rule editing, synthetic
profile and public-competition preview, differences, review, and activation
records. Preview never reads an arbitrary real student's profile and does not
persist recommendations. Submission, review, activation, and retirement write
audit evidence.

Personalized responses identify `rule_set_version` and explainable reasons but
never expose internal scores. If no valid active version exists, the endpoint
explicitly returns general actionable recommendations with a
`no_active_rule_set` fallback and exposes a configuration fault to admins. It
does not silently use service constants.

## Consequences

Recommendation behavior becomes reproducible, previewable, independently
reviewed, and reversible through activation of another version. The P2 slice
adds rule-set persistence, capabilities, UI, APIs, state tests, and audit work,
but avoids a general-purpose rules engine and prevents hidden code defaults from
becoming product behavior.
