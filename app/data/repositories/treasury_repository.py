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
        treasury_id: int | None = None,
        ref_table: str | None = None,
        ref_id: int | None = None,
        notes: str | None = None,
    ) -> int:
        # عند عدم تحديد خزنة تُسجَّل الحركة في الخزنة الافتراضية تلقائيًا.
        return self.db.insert(
            "INSERT INTO treasury(direction, category, amount, treasury_id, ref_table, "
            "ref_id, date, day_id, user_id, notes) VALUES (?, ?, ?, "
            "COALESCE(?, (SELECT id FROM treasuries WHERE is_default=1 LIMIT 1)), "
            "?, ?, ?, ?, ?, ?)",
            (direction, category, amount, treasury_id, ref_table, ref_id, date,
             day_id, user_id, notes),
        )

    def find_by_id(self, entry_id: int):
        return self.db.query_one("SELECT * FROM treasury WHERE id = ?", (entry_id,))

    def delete(self, entry_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM treasury WHERE id = ?", (entry_id,))

    def current_balance(self, treasury_id: int | None = None) -> float:
        """رصيد الصندوق (داخل ناقص خارج)؛ لكل الخزائن أو لخزنة محددة."""
        if treasury_id is None:
            row = self.db.query_one(
                "SELECT COALESCE(SUM(CASE WHEN direction='in' THEN amount "
                "ELSE -amount END), 0) AS bal FROM treasury"
            )
        else:
            row = self.db.query_one(
                "SELECT COALESCE(SUM(CASE WHEN direction='in' THEN amount "
                "ELSE -amount END), 0) AS bal FROM treasury WHERE treasury_id = ?",
                (treasury_id,),
            )
        return float(row["bal"]) if row else 0.0

    def day_totals(self, day_id: int, treasury_id: int | None = None) -> tuple[float, float]:
        """إجمالي الداخل والخارج ليوم محدّد (لكل الخزائن أو لخزنة محددة)."""
        if treasury_id is None:
            rows = self.db.query(
                "SELECT direction, COALESCE(SUM(amount), 0) AS total "
                "FROM treasury WHERE day_id = ? GROUP BY direction",
                (day_id,),
            )
        else:
            rows = self.db.query(
                "SELECT direction, COALESCE(SUM(amount), 0) AS total "
                "FROM treasury WHERE day_id = ? AND treasury_id = ? GROUP BY direction",
                (day_id, treasury_id),
            )
        total_in = 0.0
        total_out = 0.0
        for row in rows:
            if row["direction"] == "in":
                total_in = float(row["total"])
            elif row["direction"] == "out":
                total_out = float(row["total"])
        return total_in, total_out

    def list_for_day(self, day_id: int, treasury_id: int | None = None):
        if treasury_id is None:
            return self.db.query(
                """
                SELECT t.*, u.username, tr.name AS treasury_name
                FROM treasury t
                LEFT JOIN users u ON u.id = t.user_id
                LEFT JOIN treasuries tr ON tr.id = t.treasury_id
                WHERE t.day_id = ?
                ORDER BY t.id DESC
                """,
                (day_id,),
            )
        return self.db.query(
            """
            SELECT t.*, u.username, tr.name AS treasury_name
            FROM treasury t
            LEFT JOIN users u ON u.id = t.user_id
            LEFT JOIN treasuries tr ON tr.id = t.treasury_id
            WHERE t.day_id = ? AND t.treasury_id = ?
            ORDER BY t.id DESC
            """,
            (day_id, treasury_id),
        )

    def list_income_expense(self, dfrom: str, dto: str):
        """حركات الإيراد/المصروف ضمن نطاق تاريخ (للشاشة المخصّصة)."""
        return self.db.query(
            """
            SELECT t.*, u.username
            FROM treasury t LEFT JOIN users u ON u.id = t.user_id
            WHERE t.category IN ('income','expense')
              AND substr(t.date,1,10) BETWEEN ? AND ?
            ORDER BY t.id DESC
            """,
            (dfrom, dto),
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
