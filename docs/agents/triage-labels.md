# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those
roles to the actual label strings used in this repo's GitHub issue tracker.

| Label in mattpocock/skills | Label in this repo | Meaning |
|---|---|---|
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified, ready for an AFK agent |
| `ready-for-human` | `ready-for-human` | Requires human implementation |
| `wontfix` | `wontfix` | Will not be actioned |

When a skill mentions a role, use the corresponding label string from this
table.

## Operational Delivery Label

`blocked` is an operational delivery label, not a sixth triage role. It means a
known dependency or external condition prevents effective implementation from
starting.

- Use `needs-info` only when required information or a decision is missing and
  must be supplied by the reporter or owner.
- Use `blocked` when the missing condition is already known, and name it in a
  `Blocked by` section with an explicit unblock gate.
- Do not combine `blocked` with `ready-for-agent`. Remove `blocked`, reconcile
  the issue against the merged dependency, and then add `ready-for-agent`.
- A completion dependency that does not prevent useful implementation from
  starting belongs under `Completion dependencies`; it does not require the
  `blocked` label.
- Parent acceptance issues may combine `blocked` with `ready-for-human` when a
  human owner can coordinate acceptance but completion still depends on child
  issues.
