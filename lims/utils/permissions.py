"""Permission helpers bridging routes and the User model."""
from __future__ import annotations

from typing import Sequence

from flask_login import current_user

from lims.models import Result, Sample, User
from lims.models.user import UserRole, requires_roles


def require_role(roles: Sequence[str] | str | Sequence[UserRole]):
    if isinstance(roles, (str, UserRole)):
        roles = [roles]
    normalized = []
    for role in roles:
        if isinstance(role, UserRole):
            normalized.append(role.value)
        else:
            normalized.append(str(role).lower())
    return requires_roles(*normalized)


def _normalize_user(user: User | None):
    if user is None:
        return current_user
    return user


def can_edit_sample(sample: Sample, user: User | None = None) -> bool:
    user = _normalize_user(user)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if sample.collector_id == user.id:
        return True
    return user.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ANALYST))


def can_validate_sample(sample: Sample, user: User | None = None) -> bool:
    user = _normalize_user(user)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VALIDATOR))


def can_edit_result(result: Result, user: User | None = None) -> bool:
    user = _normalize_user(user)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if result.analyst_id and result.analyst_id == user.id:
        return True
    return user.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ANALYST))


def can_validate_result(result: Result, user: User | None = None) -> bool:
    user = _normalize_user(user)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VALIDATOR))
