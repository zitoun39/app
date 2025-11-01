"""User and role models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Sequence

from flask import abort
from flask_login import UserMixin, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class UserRole(Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    ANALYST = "analyst"
    VALIDATOR = "validator"
    VIEWER = "viewer"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))

    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    laboratory_id = db.Column(db.String(20))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def has_role(self, role: str | UserRole) -> bool:
        if isinstance(role, str):
            try:
                role = UserRole(role.lower())
            except ValueError:
                return False
        return self.role == role

    def has_any_role(self, roles: Sequence[str | UserRole] | set[str | UserRole]) -> bool:
        if not roles:
            return False
        for role in roles:
            if self.has_role(role):
                return True
        return False

    def require_role(self, *roles: str | UserRole) -> None:
        if not self.has_any_role(roles):
            raise PermissionError(f"User '{self.username}' lacks required role(s): {roles}")

    # Existing permission helpers remain for backwards compatibility
    @property
    def is_admin(self) -> bool:
        return self.has_role(UserRole.ADMIN)

    @property
    def is_supervisor(self) -> bool:
        return self.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR))

    @property
    def can_create_samples(self) -> bool:
        return self.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ANALYST))

    @property
    def can_enter_results(self) -> bool:
        return self.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ANALYST))

    @property
    def can_validate_results(self) -> bool:
        return self.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VALIDATOR))

    @property
    def can_generate_reports(self) -> bool:
        return self.has_any_role((UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VALIDATOR))

    @property
    def can_manage_users(self) -> bool:
        return self.has_role(UserRole.ADMIN)

    def is_account_locked(self) -> bool:
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False

    def lock_account(self, duration_minutes: int = 30) -> None:
        from datetime import timedelta

        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        db.session.commit()

    def unlock_account(self) -> None:
        self.locked_until = None
        self.failed_login_attempts = 0
        db.session.commit()

    def record_login_attempt(self, success: bool = True) -> None:
        if success:
            self.failed_login_attempts = 0
            self.last_login = datetime.utcnow()
        else:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 5:
                self.lock_account()
        db.session.commit()

    def get_permissions(self) -> list[str]:
        permissions = ["view_samples", "view_results"]
        if self.can_create_samples:
            permissions.extend(["create_samples", "edit_samples"])
        if self.can_enter_results:
            permissions.extend(["enter_results", "edit_results"])
        if self.can_validate_results:
            permissions.extend(["validate_results", "approve_results"])
        if self.can_generate_reports:
            permissions.extend(["generate_reports", "export_data"])
        if self.can_manage_users:
            permissions.extend(["manage_users", "system_settings"])
        return permissions

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "laboratory_id": self.laboratory_id,
            "department": self.department,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "permissions": self.get_permissions(),
        }

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role.value})>"


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship("User", backref="sessions")

    def is_expired(self, timeout_minutes: int = 120) -> bool:
        from datetime import timedelta

        if not self.last_activity:
            return True
        expiry_time = self.last_activity + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > expiry_time

    def update_activity(self) -> None:
        self.last_activity = datetime.utcnow()
        db.session.commit()

    def terminate(self) -> None:
        self.is_active = False
        db.session.commit()


def requires_roles(*roles: str | UserRole):
    """View decorator enforcing that current_user has one of the provided roles."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_any_role(roles):
                abort(403)
            return func(*args, **kwargs)

        return wrapper

    return decorator
