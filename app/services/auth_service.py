"""خدمة المصادقة والصلاحيات.

تتحقق من بيانات الدخول عبر PBKDF2، تحمّل صلاحيات الدور، وتحتفظ بالمستخدم
الحالي للجلسة. كما تنشئ حساب المدير في الإعداد لأول مرة.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.core.constants.setting_keys import SettingKeys
from app.core.security.password_hasher import hash_password, verify_password
from app.core.utils.formatters import now_iso
from app.data.repositories.users_repository import UsersRepository
from app.data.seed import ROLE_ADMIN
from app.domain.entities import User
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService


class AuthError(Exception):
    """خطأ مصادقة مع رسالة عربية جاهزة للعرض."""


class AuthService:
    def __init__(
        self,
        users_repo: UsersRepository,
        audit: AuditService,
        settings: SettingsService,
    ):
        self._users = users_repo
        self._audit = audit
        self._settings = settings
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
        if row is None:
            raise AuthError("اسم المستخدم أو كلمة المرور غير صحيحة.")

        # هل الحساب مقفل حاليًا بسبب محاولات فاشلة؟
        locked_until = row["locked_until"]
        now = datetime.now()
        if locked_until:
            try:
                until = datetime.fromisoformat(locked_until)
                if now < until:
                    mins = max(int((until - now).total_seconds() // 60) + 1, 1)
                    raise AuthError(
                        f"الحساب مقفل مؤقتًا بسبب محاولات دخول فاشلة. "
                        f"حاول بعد {mins} دقيقة."
                    )
            except ValueError:
                pass

        if not verify_password(password, row["password_hash"]):
            self._register_failure(row)
            raise self._failure_error(row)

        if not bool(row["is_active"]):
            raise AuthError("هذا الحساب معطّل. راجع المدير.")

        permissions = self._users.permissions_for_role(row["role_id"])
        user = User.from_row(row, permissions=permissions)
        self._users.reset_login_state(user.id)
        self._users.touch_last_login(user.id, now_iso())
        self._current_user = user
        self._audit.log("login", user_id=user.id, entity="users", entity_id=user.id)
        return user

    def _register_failure(self, row) -> None:
        max_attempts = self._settings.get_int(SettingKeys.LOGIN_MAX_ATTEMPTS, 5)
        lock_min = self._settings.get_int(SettingKeys.LOGIN_LOCKOUT_MINUTES, 15)
        attempts = (row["failed_attempts"] or 0) + 1
        if attempts >= max_attempts:
            locked_until = (datetime.now() + timedelta(minutes=lock_min)).isoformat()
            self._users.register_failed_login(row["id"], 0, locked_until)
            self._audit.log(
                "login_locked", user_id=row["id"], entity="users",
                entity_id=row["id"], details=f"locked {lock_min}m",
            )
        else:
            self._users.register_failed_login(row["id"], attempts, None)

    def _failure_error(self, row) -> AuthError:
        max_attempts = self._settings.get_int(SettingKeys.LOGIN_MAX_ATTEMPTS, 5)
        lock_min = self._settings.get_int(SettingKeys.LOGIN_LOCKOUT_MINUTES, 15)
        attempts = (row["failed_attempts"] or 0) + 1
        if attempts >= max_attempts:
            return AuthError(
                f"تم قفل الحساب {lock_min} دقيقة بسبب تكرار محاولات الدخول الفاشلة."
            )
        remaining = max_attempts - attempts
        return AuthError(
            f"اسم المستخدم أو كلمة المرور غير صحيحة. محاولات متبقية: {remaining}."
        )

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
