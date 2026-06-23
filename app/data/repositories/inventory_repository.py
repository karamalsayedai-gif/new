"""مستودع المخزون (أصناف/قطع الغيار) وحركة المخزون."""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository
from app.domain.entities import InventoryItem


class InventoryRepository(BaseRepository):
    # ── الأصناف ─────────────────────────────────────────────────────────
    def create(
        self,
        *,
        name: str,
        category: str,
        unit: str,
        quantity: float,
        min_stock: float,
        unit_cost: float,
        sale_price: float,
        status: str,
        created_at: str,
    ) -> int:
        return self.db.insert(
            "INSERT INTO inventory_items(name, category, unit, quantity, "
            "min_stock, unit_cost, sale_price, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, category, unit, quantity, min_stock, unit_cost, sale_price,
             status, created_at),
        )

    def update(
        self,
        item_id: int,
        *,
        name: str,
        category: str,
        unit: str,
        min_stock: float,
        unit_cost: float,
        sale_price: float,
        status: str,
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE inventory_items SET name=?, category=?, unit=?, "
                "min_stock=?, unit_cost=?, sale_price=?, status=? WHERE id=?",
                (name, category, unit, min_stock, unit_cost, sale_price, status,
                 item_id),
            )

    def delete(self, item_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM inventory_items WHERE id=?", (item_id,))

    def find_by_id(self, item_id: int) -> InventoryItem | None:
        row = self.db.query_one(
            "SELECT * FROM inventory_items WHERE id=?", (item_id,)
        )
        return InventoryItem.from_row(row) if row else None

    def has_sales(self, item_id: int) -> bool:
        row = self.db.query_one(
            "SELECT 1 FROM sale_items WHERE item_id=? LIMIT 1", (item_id,)
        )
        return row is not None

    def categories(self) -> list[str]:
        rows = self.db.query(
            "SELECT DISTINCT category FROM inventory_items "
            "WHERE category IS NOT NULL AND category <> '' ORDER BY category"
        )
        return [r["category"] for r in rows]

    def list_items(
        self,
        *,
        search: str = "",
        category: str = "",
        status: str = "",
        only_low: bool = False,
    ) -> list[InventoryItem]:
        clauses: list[str] = []
        params: list[object] = []
        if search.strip():
            like = f"%{search.strip()}%"
            clauses.append("(name LIKE ? OR category LIKE ?)")
            params.extend([like, like])
        if category:
            clauses.append("category = ?")
            params.append(category)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if only_low:
            clauses.append("min_stock > 0 AND quantity <= min_stock")

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.db.query(
            f"SELECT * FROM inventory_items{where} ORDER BY name", tuple(params)
        )
        return [InventoryItem.from_row(r) for r in rows]

    def list_low_stock(self, default_threshold: int = 0) -> list[InventoryItem]:
        # صنف يُعدّ ناقصًا إن كان له حد أدنى وتجاوزه، أو (إن لم يُحدَّد له حد)
        # نزل عن حد التنبيه العام من الإعدادات.
        rows = self.db.query(
            "SELECT * FROM inventory_items "
            "WHERE status='active' AND ("
            "  (min_stock > 0 AND quantity <= min_stock)"
            "  OR (min_stock = 0 AND ? > 0 AND quantity <= ?)"
            ") ORDER BY name",
            (default_threshold, default_threshold),
        )
        return [InventoryItem.from_row(r) for r in rows]

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS c FROM inventory_items")
        return int(row["c"]) if row else 0

    # ── حركة المخزون ────────────────────────────────────────────────────
    def record_movement(
        self,
        *,
        item_id: int,
        direction: str,
        quantity: float,
        reason: str | None,
        user_id: int | None,
        created_at: str,
        ref_table: str | None = None,
        ref_id: int | None = None,
    ) -> int:
        """تسجيل حركة وتعديل الكمية في معاملة واحدة."""
        delta = quantity if direction == "in" else -quantity
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO stock_movements(item_id, direction, quantity, reason, "
                "ref_table, ref_id, user_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (item_id, direction, quantity, reason, ref_table, ref_id, user_id,
                 created_at),
            )
            conn.execute(
                "UPDATE inventory_items SET quantity = quantity + ? WHERE id=?",
                (delta, item_id),
            )
            return int(cur.lastrowid)

    def list_movements(self, item_id: int, limit: int = 100):
        return self.db.query(
            """
            SELECT m.*, u.username
            FROM stock_movements m LEFT JOIN users u ON u.id = m.user_id
            WHERE m.item_id = ? ORDER BY m.id DESC LIMIT ?
            """,
            (item_id, limit),
        )
