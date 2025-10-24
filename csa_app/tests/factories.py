"""Helper factories for tests."""

from __future__ import annotations

from typing import Sequence

from app.extensions import db
from app.models import Role, User, UserStatus


def _ensure_role(name: str) -> Role:
    role = Role.query.filter_by(name=name).first()
    if role is None:
        role = Role(name=name)
        db.session.add(role)
        db.session.flush()
    return role


def create_user(
    email: str,
    password: str,
    *,
    status: UserStatus = UserStatus.ACTIVE,
    roles: Sequence[str] | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    user = User(
        email=email,
        status=status,
        first_name=first_name,
        last_name=last_name,
    )
    user.set_password(password)

    if roles:
        for role_name in roles:
            role = _ensure_role(role_name)
            user.roles.append(role)

    db.session.add(user)
    db.session.commit()
    return user