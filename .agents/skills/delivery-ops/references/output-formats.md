# Delivery Ops Output Formats

Use only the format needed for the selected branch. Keep outputs concise and
include `Assumptions / Missing Reality` when reality is incomplete.

## Daily Delivery Board

```markdown
# Daily Delivery Board

## Reality Check
- Date:
- Roadmap phase:
- Milestone / deadline:
- Latest standup used:
- GitHub status:
- Assumptions / Missing Reality:

## Current Target
- Demo-critical path:
- Today focus:

## Must Finish Today
| Work | DRI | Reviewer | Validation Owner | Risk | Next Action |
| --- | --- | --- | --- | --- | --- |

## Should Finish Today
| Work | DRI | Reviewer | Validation Owner | Risk | Next Action |
| --- | --- | --- | --- | --- | --- |

## Blocked / Needs Decision
| Work | Blocker | Decision Needed | Owner |
| --- | --- | --- | --- |

## PR Review Queue
| PR | Linked Work | Status | Missing Evidence | Recommendation |
| --- | --- | --- | --- | --- |

## Merge Candidates
| PR | Why Ready | Remaining Risk | Suggested Squash Message |
| --- | --- | --- | --- |

## Deferred
| Work | Reason | Revisit After |
| --- | --- | --- |
```

## Issue Preview

```markdown
# Issue Preview

## Title

## Labels

## Body

### Goal

### Scope
Included:
-

Out of scope:
-

### Acceptance Criteria
- [ ]

### Affected Surfaces
-

### Validation Plan
-

### Delivery Ownership
- DRI:
- Contributors:
  - Active:
  - Align with:
  - FYI:
- Reviewer:
- Validation owner:
- Docs impact:

### Source Links
-

## Not Ready Until
-
```

## PR Readiness Review

```markdown
# PR Readiness Review

## Verdict
Ready / Not ready / Risky

## Linked Work

## Product Fit

## Scope Control

## Technical / Design Risks

## Validation Evidence

## Docs Impact

## Required Changes Before Merge

## Suggested Review Comment

## Suggested Squash Commit Message
```

## Merge Queue

```markdown
# Merge Queue

## Reality Check
- Deadline:
- Latest standup used:
- GitHub status:
- Risk acceptance needed:

## Merge Candidates
| Order | PR | Linked Work | Checks / Review | Docs Impact | Remaining Risk | Squash Message |
| --- | --- | --- | --- | --- | --- | --- |

## Risky / Blocked
| PR | Blocker | Required Decision |
| --- | --- | --- |

## Final Confirmation Needed
-
```

## Morning Standup Preview

```markdown
# Morning Standup Preview

## Target File
`docs/meetings/YYYY-MM-DD-standup-0.md`

## Focus
- Roadmap phase:
- Today target:
- Operating rule:

## Owner List
| Issue | DRI | Contributors | Reviewer | Validation owner | Docs impact | Status | Blocker | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Needs Issue Preview
-
```

## Evening Standup Update

```markdown
# Evening Standup Update

## Target File
`docs/meetings/YYYY-MM-DD-standup-0.md`

## Owner List Updates
| Issue | Status Change | Blocker | Next Action |
| --- | --- | --- | --- |

## Notes
- Decision:
- Risk:
- Follow-up:

## Tomorrow Carry-over
-

## Needs Reconciliation
-
```
