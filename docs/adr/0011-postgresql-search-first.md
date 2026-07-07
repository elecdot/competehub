# ADR 0011: PostgreSQL Search First

## Status

Accepted

## Context

Competition discovery needs keyword search and structured filtering, but the current data volume and product risk do not justify a dedicated search service. Elasticsearch, Meilisearch, or a Chinese segmentation service would add Docker services, index synchronization, consistency rules, deployment work, and tuning cost before the core publication, discovery, subscription, reminder, and recommendation loops are validated.

## Decision

Use PostgreSQL-backed filters and simple keyword matching for the current search implementation. Do not add Elasticsearch, Meilisearch, or a dedicated Chinese search service for P1/P2. PostgreSQL remains the source of truth for competition data; any future search index must be a derived view.

## Consequences

The initial implementation can focus on reliable data, state, permissions, reminders, and explainable recommendation. Revisit this decision only when competition volume grows substantially, users report search quality as a clear product problem, synonym or typo handling becomes necessary, complex Chinese segmentation is required, or PostgreSQL search materially slows the core list and detail workflows.
