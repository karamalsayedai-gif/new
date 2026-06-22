"""مستودع المستخدمين والأدوار والصلاحيات."""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository
from app.domain.entities import Role, User


class UsersRepository(BaseRepository):
    # ── المستخدمون ──────────────────────────────────────────────────────
    def count_users(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS c FROM users")
        return int(row["c"]) if row else 0

    def create_user(
        self,
        username: str,
        full_name: str,
        password_hash: str,
        role_id: int,
        is_active: bool = True,
        created_at: str = "",
    ) -> int:
        return self.db.insert(
            "INSERT INTO users(username, full_name, password_hash, role_id, "
            "is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (username, full_name, password_hash, role_id, int(is_active), created_at),
        )

    def find_by_username(self, username: str):
        return self.db.query_one(
            """
            SELECT u.*, r.name AS role_name
            FROM users u JOIN roles r ON r.id = u.role_id
            WHERE u.username = ?
            """,
            (username.strip(),),
        )

    def list_users(self) -> list[User]:
        rows = self.db.query(
            """
            SELECT u.*, r.name AS role_name
            FROM users u JOIN roles r ON r.id = u.role_id
            ORDER BY u.id
            """
        )
        return [User.from_row(r) for r in rows]

    def set_active(self, user_id: int, active: bool) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET is_active = ? WHERE id = ?",
                (int(active), user_id),
            )

    def update_password(self, user_id: int, password_hash: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )

    def touch_last_login(self, user_id: int, when: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?",
                (when, user_id),
            )

    # ── الأدوار والصلاحيات ──────────────────────────────────────────────
    def list_roles(self) -> list[Role]:
        rows = self.db.query("SELECT * FROM roles ORDER BY id")
        return [Role.from_row(r) for r in rows]

    def find_role_by_name(self, name: str) -> int | None:
        row = self.db.query_one("SELECT id FROM roles WHERE name = ?", (name,))
        return int(row["id"]) if row else None

    def permissions_for_role(self, role_id: int) -> set[str]:
        rows = self.db.query(
            "SELECT permission_code FROM role_permissions WHERE role_id = ?",
            (role_id,),
        )
        return {r["permission_code"] for r in rows}

    def set_role_permissions(self, role_id: int, codes: set[str]) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM role_permissions WHERE role_id = ?", (role_id,)
            )
            conn.executemany(
                "INSERT INTO role_permissions(role_id, permission_code) VALUES (?, ?)",
                [(role_id, code) for code in codes],
            )
