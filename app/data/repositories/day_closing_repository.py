"""مستودع الإقفال اليومي والحركات النقدية المرتبطة باليوم."""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository


class DayClosingRepository(BaseRepository):
    def find_by_date(self, business_date: str):
        return self.db.query_one(
            "SELECT * FROM day_closings WHERE business_date = ?", (business_date,)
        )

    def find_by_id(self, day_id: int):
        return self.db.query_one(
            "SELECT * FROM day_closings WHERE id = ?", (day_id,)
        )

    def last_closed_counted(self) -> float:
        """آخر رصيد نقدي معدود من يوم مُقفل (يصبح رصيد افتتاح اليوم التالي)."""
        row = self.db.query_one(
            "SELECT counted_cash FROM day_closings WHERE status = 'closed' "
            "ORDER BY business_date DESC LIMIT 1"
        )
        if row is None or row["counted_cash"] is None:
            return 0.0
        return float(row["counted_cash"])

    def open_day(self, business_date: str, opening_balance: float, opened_at: str) -> int:
        return self.db.insert(
            "INSERT INTO day_closings(business_date, opening_balance, status, "
            "opened_at) VALUES (?, ?, 'open', ?)",
            (business_date, opening_balance, opened_at),
        )

    def treasury_net_for_day(self, day_id: int) -> float:
        """صافي حركة الخزينة لليوم: مجموع الداخل ناقص الخارج."""
        row = self.db.query_one(
            """
            SELECT COALESCE(SUM(CASE WHEN direction = 'in' THEN amount
                                     ELSE -amount END), 0) AS net
            FROM treasury WHERE day_id = ?
            """,
            (day_id,),
        )
        return float(row["net"]) if row else 0.0

    def close_day(
        self,
        day_id: int,
        expected_cash: float,
        counted_cash: float,
        difference: float,
        closed_by: int,
        closed_at: str,
        notes: str | None,
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE day_closings
                SET expected_cash = ?, counted_cash = ?, difference = ?,
                    status = 'closed', closed_by = ?, closed_at = ?, notes = ?
                WHERE id = ?
                """,
                (expected_cash, counted_cash, difference, closed_by, closed_at,
                 notes, day_id),
            )

    def set_status(self, day_id: int, status: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE day_closings SET status = ? WHERE id = ?", (status, day_id)
            )
