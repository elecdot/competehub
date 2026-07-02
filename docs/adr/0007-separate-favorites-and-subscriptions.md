# ADR 0007: Separate Favorites and Subscriptions

**Status**: Accepted.

CompeteHub will model favorites and subscriptions as separate student actions. A favorite is a lightweight saved reference for later viewing; it does not create reminder records or personal calendar entries. A subscription means the student has chosen to follow the competition time nodes, so it can drive in-app reminders and the personal competition calendar. Merging these concepts into one "follow" state would simplify the UI at first, but it would make reminder consent, API behavior, data cleanup, and student expectations ambiguous.
