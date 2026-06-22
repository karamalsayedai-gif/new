"""خدمة إدارة المستخدمين والأدوار (منطق العمل فوق المستودع)."""
from __future__ import annotations

from app.core.security.password_hasher import hash_password
from app.core.utils.formatters import now_iso
from app.data.repositories.users_repository import UsersRepository
from app.domain.entities import Role, User
from app.services.audit_service import AuditService


class UsersServiceError(Exception):
    """خطأ في إدارة المستخدمين مع رسالة عربية."""


class UsersService:
    def __init__(self, repo: UsersRepository, audit: AuditService):
        self._repo = repo
        self._audit = audit

    def list_users(self) -> list[User]:
        return self._repo.list_users()

    def list_roles(self) -> list[Role]:
        return self._repo.list_roles()

    def create_user(
        self,
        username: str,
        full_name: str,
        password: str,
        role_id: int,
        actor_id: int | None = None,
    ) -> int:
        username = username.strip()
        if not username or not password or not full_name.strip():
            raise UsersServiceError("الاسم واسم المستخدم وكلمة المرور مطلوبة.")
        if self._repo.find_by_username(username) is not None:
            raise UsersServiceError("اسم المستخدم مستخدم بالفعل.")
        user_id = self._repo.create_user(
            username=username,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
            role_id=role_id,
            is_active=True,
            created_at=now_iso(),
        )
        self._audit.log(
            "user_create", user_id=actor_id, entity="users", entity_id=user_id
        )
        return user_id

    def set_active(self, user_id: int, active: bool, actor_id: int | None = None) -> None:
        self._repo.set_active(user_id, active)
        self._audit.log(
            "user_activate" if active else "user_deactivate",
            user_id=actor_id,
            entity="users",
            entity_id=user_id,
        )

    def reset_password(
        self, user_id: int, new_password: str, actor_id: int | None = None
    ) -> None:
        if len(new_password) < 4:
            raise UsersServiceError("كلمة المرور قصيرة جدًا.")
        self._repo.update_password(user_id, hash_password(new_password))
        self._audit.log(
            "user_reset_password", user_id=actor_id, entity="users", entity_id=user_id
        )

    def role_permissions(self, role_id: int) -> set[str]:
        return self._repo.permissions_for_role(role_id)

    def set_role_permissions(
        self, role_id: int, codes: set[str], actor_id: int | None = None
    ) -> None:
        self._repo.set_role_permissions(role_id, codes)
        self._audit.log(
            "role_permissions_update",
            user_id=actor_id,
            entity="roles",
            entity_id=role_id,
        )
