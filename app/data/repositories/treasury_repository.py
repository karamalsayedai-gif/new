"""مستودع الخزينة (الصندوق الرئيسي): حركات الدخل والصرف."""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository


class TreasuryRepository(BaseRepository):
    def add(
        self,
        *,
        direction: str,
        category: str,
        amount: float,
        date: str,
        day_id: int,
        user_id: int | None,
        ref_table: str | None = None,
        ref_id: int | None = None,
        notes: str | None = None,
    ) -> int:
        return self.db.insert(
            "INSERT INTO treasury(direction, category, amount, ref_table, ref_id, "
            "date, day_id, user_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (direction, category, amount, ref_table, ref_id, date, day_id,
             user_id, notes),
        )

    def find_by_id(self, entry_id: int):
        return self.db.query_one("SELECT * FROM treasury WHERE id = ?", (entry_id,))

    def delete(self, entry_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM treasury WHERE id = ?", (entry_id,))

    def current_balance(self) -> float:
        """رصيد الصندوق الكلّي عبر كل الأيام (داخل ناقص خارج)."""
        row = self.db.query_one(
            "SELECT COALESCE(SUM(CASE WHEN direction='in' THEN amount "
            "ELSE -amount END), 0) AS bal FROM treasury"
        )
        return float(row["bal"]) if row else 0.0

    def day_totals(self, day_id: int) -> tuple[float, float]:
        """إجمالي الداخل والخارج ليوم محدّد."""
        rows = self.db.query(
            "SELECT direction, COALESCE(SUM(amount), 0) AS total "
            "FROM treasury WHERE day_id = ? GROUP BY direction",
            (day_id,),
        )
        total_in = 0.0
        total_out = 0.0
        for row in rows:
            if row["direction"] == "in":
                total_in = float(row["total"])
            elif row["direction"] == "out":
                total_out = float(row["total"])
        return total_in, total_out

    def list_for_day(self, day_id: int):
        return self.db.query(
            """
            SELECT t.*, u.username
            FROM treasury t LEFT JOIN users u ON u.id = t.user_id
            WHERE t.day_id = ?
            ORDER BY t.id DESC
            """,
            (day_id,),
        )

    def list_recent(self, limit: int = 200):
        return self.db.query(
            """
            SELECT t.*, u.username
            FROM treasury t LEFT JOIN users u ON u.id = t.user_id
            ORDER BY t.id DESC LIMIT ?
            """,
            (limit,),
        )
