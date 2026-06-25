"""مستودع الخزائن المتعددة (الصندوق الرئيسي + محافظ مثل فودافون كاش + بنوك…)."""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository


class TreasuriesRepository(BaseRepository):
    def list_all(self):
        return self.db.query(
            "SELECT * FROM treasuries ORDER BY is_default DESC, name"
        )

    def list_active(self):
        return self.db.query(
            "SELECT * FROM treasuries WHERE is_active = 1 ORDER BY is_default DESC, name"
        )

    def find_by_id(self, treasury_id: int):
        return self.db.query_one(
            "SELECT * FROM treasuries WHERE id = ?", (treasury_id,)
        )

    def default_id(self) -> int | None:
        row = self.db.query_one(
            "SELECT id FROM treasuries WHERE is_default = 1 LIMIT 1"
        )
        return int(row["id"]) if row else None

    def create(self, *, name: str, kind: str, created_at: str) -> int:
        return self.db.insert(
            "INSERT INTO treasuries(name, kind, is_default, is_active, created_at) "
            "VALUES (?, ?, 0, 1, ?)",
            (name, kind, created_at),
        )

    def update(self, treasury_id: int, *, name: str, kind: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE treasuries SET name = ?, kind = ? WHERE id = ?",
                (name, kind, treasury_id),
            )

    def set_active(self, treasury_id: int, active: bool) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE treasuries SET is_active = ? WHERE id = ?",
                (1 if active else 0, treasury_id),
            )

    def has_movements(self, treasury_id: int) -> bool:
        row = self.db.query_one(
            "SELECT 1 FROM treasury WHERE treasury_id = ? LIMIT 1", (treasury_id,)
        )
        return row is not None

    def delete(self, treasury_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM treasuries WHERE id = ?", (treasury_id,))

    def balance(self, treasury_id: int) -> float:
        row = self.db.query_one(
            "SELECT COALESCE(SUM(CASE WHEN direction='in' THEN amount "
            "ELSE -amount END), 0) AS bal FROM treasury WHERE treasury_id = ?",
            (treasury_id,),
        )
        return float(row["bal"]) if row else 0.0

    def balances(self):
        """كل الخزائن مع رصيد كل واحدة."""
        return self.db.query(
            """
            SELECT tr.*, COALESCE(SUM(CASE WHEN t.direction='in' THEN t.amount
                                          ELSE -t.amount END), 0) AS balance
            FROM treasuries tr
            LEFT JOIN treasury t ON t.treasury_id = tr.id
            GROUP BY tr.id
            ORDER BY tr.is_default DESC, tr.name
            """
        )
