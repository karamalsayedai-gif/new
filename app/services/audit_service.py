"""خدمة سجل التدقيق: تسجيل كل إجراء حسّاس + بحث مُفلتر للعرض الإداري."""
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

    def search(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        user_id: int | None = None,
        entity: str | None = None,
        action: str | None = None,
        text: str | None = None,
        limit: int = 2000,
    ):
        """بحث مُفلتر في السجل (نطاق تاريخ From/To + مستخدم + وحدة + عملية + نص)."""
        clauses: list[str] = []
        params: list[object] = []
        if date_from:
            clauses.append("substr(a.created_at,1,10) >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("substr(a.created_at,1,10) <= ?")
            params.append(date_to)
        if user_id is not None:
            clauses.append("a.user_id = ?")
            params.append(user_id)
        if entity:
            clauses.append("a.entity = ?")
            params.append(entity)
        if action:
            clauses.append("a.action = ?")
            params.append(action)
        if text and text.strip():
            like = f"%{text.strip()}%"
            clauses.append("(a.action LIKE ? OR a.details LIKE ? OR u.username LIKE ?)")
            params.extend([like, like, like])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        return self._db.query(
            f"""
            SELECT a.*, u.username
            FROM audit_log a LEFT JOIN users u ON u.id = a.user_id
            {where}
            ORDER BY a.id DESC LIMIT ?
            """,
            tuple(params),
        )

    def entities(self) -> list[str]:
        rows = self._db.query(
            "SELECT DISTINCT entity FROM audit_log WHERE entity IS NOT NULL "
            "AND entity <> '' ORDER BY entity"
        )
        return [r["entity"] for r in rows]

    def actions(self) -> list[str]:
        rows = self._db.query(
            "SELECT DISTINCT action FROM audit_log ORDER BY action"
        )
        return [r["action"] for r in rows]
