"""مستودع الموردين."""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository
from app.domain.entities import Supplier


class SuppliersRepository(BaseRepository):
    def create(
        self, *, name: str, phone: str, address: str, created_at: str
    ) -> int:
        return self.db.insert(
            "INSERT INTO suppliers(name, phone, address, balance, created_at) "
            "VALUES (?, ?, ?, 0, ?)",
            (name, phone, address, created_at),
        )

    def update(
        self, supplier_id: int, *, name: str, phone: str, address: str
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE suppliers SET name=?, phone=?, address=? WHERE id=?",
                (name, phone, address, supplier_id),
            )

    def delete(self, supplier_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))

    def find_by_id(self, supplier_id: int) -> Supplier | None:
        row = self.db.query_one(
            "SELECT * FROM suppliers WHERE id=?", (supplier_id,)
        )
        return Supplier.from_row(row) if row else None

    def has_purchases(self, supplier_id: int) -> bool:
        row = self.db.query_one(
            "SELECT 1 FROM purchases WHERE supplier_id=? LIMIT 1", (supplier_id,)
        )
        return row is not None

    def list_all(self, search: str = "") -> list[Supplier]:
        if search.strip():
            like = f"%{search.strip()}%"
            rows = self.db.query(
                "SELECT * FROM suppliers WHERE name LIKE ? OR phone LIKE ? "
                "ORDER BY name",
                (like, like),
            )
        else:
            rows = self.db.query("SELECT * FROM suppliers ORDER BY name")
        return [Supplier.from_row(r) for r in rows]

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS c FROM suppliers")
        return int(row["c"]) if row else 0

    # ── كشف الحساب / الحركات ────────────────────────────────────────────
    def purchases(self, supplier_id: int):
        return self.db.query(
            "SELECT * FROM purchases WHERE supplier_id=? ORDER BY id DESC",
            (supplier_id,),
        )

    def payments(self, supplier_id: int):
        """دفعات للمورّد مسجّلة في الخزينة (مرتبطة بمشترياته)."""
        return self.db.query(
            """
            SELECT t.* FROM treasury t
            WHERE t.ref_table = 'purchases' AND t.ref_id IN (
                SELECT id FROM purchases WHERE supplier_id = ?
            )
            ORDER BY t.id DESC
            """,
            (supplier_id,),
        )

    def adjust_balance(self, supplier_id: int, delta: float) -> None:
        """تعديل رصيد المورّد (يُستخدم لاحقًا من وحدة المشتريات)."""
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE suppliers SET balance = balance + ? WHERE id=?",
                (delta, supplier_id),
            )
