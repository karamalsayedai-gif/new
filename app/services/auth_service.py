"""خدمة المصادقة والصلاحيات.

تتحقق من بيانات الدخول عبر PBKDF2، تحمّل صلاحيات الدور، وتحتفظ بالمستخدم
الحالي للجلسة. كما تنشئ حساب المدير في الإعداد لأول مرة.
"""
from __future__ import annotations

from app.core.security.password_hasher import hash_password, verify_password
from app.core.utils.formatters import now_iso
from app.data.repositories.users_repository import UsersRepository
from app.data.seed import ROLE_ADMIN
from app.domain.entities import User
from app.services.audit_service import AuditService


class AuthError(Exception):
    """خطأ مصادقة مع رسالة عربية جاهزة للعرض."""


class AuthService:
    def __init__(self, users_repo: UsersRepository, audit: AuditService):
        self._users = users_repo
        self._audit = audit
        self._current_user: User | None = None

    @property
    def current_user(self) -> User | None:
        return self._current_user

    @property
    def is_authenticated(self) -> bool:
        return self._current_user is not None

    def can(self, permission_code: str) -> bool:
        return self._current_user is not None and self._current_user.can(
            permission_code
        )

    # ── الدخول/الخروج ───────────────────────────────────────────────────
    def login(self, username: str, password: str) -> User:
        row = self._users.find_by_username(username)
        if row is None or not verify_password(password, row["password_hash"]):
            raise AuthError("اسم المستخدم أو كلمة المرور غير صحيحة.")
        if not bool(row["is_active"]):
            raise AuthError("هذا الحساب معطّل. راجع المدير.")

        permissions = self._users.permissions_for_role(row["role_id"])
        user = User.from_row(row, permissions=permissions)
        self._users.touch_last_login(user.id, now_iso())
        self._current_user = user
        self._audit.log("login", user_id=user.id, entity="users", entity_id=user.id)
        return user

    def logout(self) -> None:
        if self._current_user is not None:
            self._audit.log("logout", user_id=self._current_user.id)
        self._current_user = None

    # ── الإعداد لأول مرة ────────────────────────────────────────────────
    def create_first_admin(
        self, username: str, full_name: str, password: str
    ) -> User:
        if self._users.count_users() > 0:
            raise AuthError("يوجد مستخدمون بالفعل؛ لا يمكن إنشاء مدير أوّلي.")
        admin_role_id = self._users.find_role_by_name(ROLE_ADMIN)
        if admin_role_id is None:
            raise AuthError("دور المدير غير موجود في قاعدة البيانات.")

        user_id = self._users.create_user(
            username=username.strip(),
            full_name=full_name.strip(),
            password_hash=hash_password(password),
            role_id=admin_role_id,
            is_active=True,
            created_at=now_iso(),
        )
        permissions = self._users.permissions_for_role(admin_role_id)
        user = User(
            id=user_id,
            username=username.strip(),
            full_name=full_name.strip(),
            role_id=admin_role_id,
            is_active=True,
            role_name=ROLE_ADMIN,
            permissions=permissions,
        )
        self._current_user = user
        self._audit.log(
            "create_first_admin", user_id=user_id, entity="users", entity_id=user_id
        )
        return user
