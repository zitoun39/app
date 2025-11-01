from __future__ import annotations

import pytest
from flask_login import login_user, logout_user

from extensions import db, login_manager
from lims.models.user import User, UserRole, requires_roles


def test_role_helpers(app):
    with app.app_context():
        user = User(
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
        )
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        assert user.has_role(UserRole.ADMIN)
        assert user.has_role("admin")
        assert user.has_any_role([UserRole.ADMIN, UserRole.VIEWER])
        assert not user.has_any_role([UserRole.VIEWER])

        with pytest.raises(PermissionError):
            user.require_role(UserRole.VIEWER)

        @requires_roles(UserRole.ADMIN)
        def protected():
            return "allowed"

        with app.test_request_context("/"):
            login_user(user)
            assert protected() == "allowed"
            logout_user()

        @requires_roles(UserRole.VALIDATOR)
        def forbidden():
            return "forbidden"

        with app.test_request_context("/"):
            login_user(user)
            with pytest.raises(Exception):
                forbidden()
            logout_user()
