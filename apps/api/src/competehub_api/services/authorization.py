from __future__ import annotations

from competehub_api.models import User


def user_has_capability(user: User, capability: str) -> bool:
    """Compatibility seam for the persisted capabilities delivered by Issue #34."""

    capabilities = getattr(user, "capabilities", ()) or ()
    return capability in capabilities
