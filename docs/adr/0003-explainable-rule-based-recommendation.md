# ADR 0003: Explainable Rule-Based Recommendation

## Status

Accepted

## Context

CompeteHub includes "智能筛选与推荐" in its formal Chinese name, so future contributors may assume the current version should expose a public competition score, "含金量" ranking, or model-based recommendation. The product boundary instead requires trustworthy and explainable student guidance: recommendation output must be traceable to student profile fields, competition tags, time nodes, and explicit configuration, and it must not replace official school or organizer recognition.

## Decision

Use explainable rule-based recommendation for the current version. Recommendation may use internal ordering weights, but public UI and reports must show recommendation reasons rather than an absolute competition value score. Model-based ranking, public scoring, and "含金量评分" are future possibilities only if data volume, evaluation criteria, governance, and user-facing explanation rules are explicitly revisited.

## Consequences

- Recommendation can ship with limited initial data and remain understandable to students and reviewers.
- Admin configuration should focus on rule weights, tags, dictionaries, and reason templates.
- API and UI design should distinguish internal ranking score from public value judgment.
- Future model-based recommendation or public scoring requires a new ADR and updates to product, API, data-model, and report documents.
