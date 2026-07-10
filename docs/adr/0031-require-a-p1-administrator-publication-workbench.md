# ADR 0031: Require a P1 Administrator Publication Workbench

## Status

Accepted

## Context

The publication feature PRD allowed API-only, CLI, seed, or an optional minimal
administrator surface even after the product adopted series and editions,
structured stages, paired milestones, immutable revisions, independent review,
diff and impact inspection, and emergency offline. Those behaviors cannot be
operated safely by administrators through a student UI or raw API calls. API
acceptance alone would prove backend rules but not a usable product workflow.

ADR 0010 originally deferred Playwright until after the whole main workflow was
stable. Once the governance workbench became a P1 requirement, its cross-role
handoff became stable and risky enough to automate when that UI is delivered.

## Decision

P1 includes a required administrator governance workbench. Editors select or
create a series and edition, maintain source-backed revision fields, organize
stages and paired milestones, set prominence, inspect completeness, save drafts,
and submit revisions. Reviewers use a queue and inspect submitter, source facts,
field/stage/node differences, and public/reminder impact before approving,
rejecting, or returning with a comment.

Status maintainers can cancel, archive, expire, or emergency-offline an edition.
The UI previews visibility and reminder consequences and requires a reason where
the domain contract requires one. Emergency-offline restoration still requires
a corrected revision and independent review. Self-review is blocked in both UI
and API.

CLI and seed paths remain setup and test tools. API-only acceptance is an
implementation milestone, not P1 product completion. When the workbench is
implemented, the project adds Playwright as a regular frontend test dependency
and a repository recipe. The first required E2E flow uses distinct editor and
reviewer accounts from revision creation through student visibility. Manual
acceptance supplements rather than replaces that path.

## Consequences

The administrator audience receives an operable, reviewable workflow consistent
with the domain model. P1 frontend scope and test setup increase, but the most
dangerous cross-role behavior gains repeatable evidence. ADR 0010 continues to
stage component testing and broader E2E coverage, while this decision advances
the publication-path Playwright gate.
