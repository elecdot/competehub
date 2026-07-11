from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "student"
    ADMIN = "admin"
    TEACHER = "teacher"
    ORGANIZER = "organizer"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class CompetitionStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    OFFLINE = "offline"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ParticipantForm(StrEnum):
    INDIVIDUAL = "individual"
    TEAM = "team"


class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"


class RecommendationRuleSetStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    REJECTED = "rejected"
    RETURNED = "returned"
    RETIRED = "retired"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    INVALID = "invalid"
