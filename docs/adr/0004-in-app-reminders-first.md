# ADR 0004: In-App Reminders First

**Status**: Accepted.

CompeteHub will deliver current-version reminders only as in-app system messages generated from subscriptions and competition time nodes. We are deliberately deferring email, SMS, WeChat, enterprise messaging, mini-program push, and external calendar sync because they introduce consent and account binding, delivery failure handling, provider cost, privacy review, and third-party operational dependencies before the core discovery-subscription-reminder loop is validated. If external notification channels become part of the product, they need a new decision record plus updates to product, API, privacy/security, and operations documentation.
