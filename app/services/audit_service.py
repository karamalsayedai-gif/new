"""خدمة سجل التدقيق: تسجيل كل إجراء حسّاس في جدول audit_log."""
from __future__ import annotations

from app.core.utils.formatters import now_iso
from app.data.database import Database


class AuditService:
    def __init__(self, db: Database):
        self._db = db

    def log(
        self,
        action: str,
        *,
        user_id: int | None = None,
        entity: str | None = None,
        entity_id: int | None = None,
        details: str | None = None,
    ) -> None:
        self._db.insert(
            "INSERT INTO audit_log(user_id, action, entity, entity_id, details, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, action, entity, entity_id, details, now_iso()),
        )

    def recent(self, limit: int = 200):
        return self._db.query(
            """
            SELECT a.*, u.username
            FROM audit_log a LEFT JOIN users u ON u.id = a.user_id
            ORDER BY a.id DESC LIMIT ?
            """,
            (limit,),
        )
