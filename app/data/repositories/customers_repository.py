"""مستودع العملاء."""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository
from app.domain.entities import Customer


class CustomersRepository(BaseRepository):
    def create(
        self,
        *,
        name: str,
        phone: str,
        national_id: str,
        address: str,
        created_at: str,
    ) -> int:
        return self.db.insert(
            "INSERT INTO customers(name, phone, national_id, address, balance, "
            "created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (name, phone, national_id, address, created_at),
        )

    def update(
        self,
        customer_id: int,
        *,
        name: str,
        phone: str,
        national_id: str,
        address: str,
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE customers SET name=?, phone=?, national_id=?, address=? "
                "WHERE id=?",
                (name, phone, national_id, address, customer_id),
            )

    def delete(self, customer_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))

    def find_by_id(self, customer_id: int) -> Customer | None:
        row = self.db.query_one(
            "SELECT * FROM customers WHERE id=?", (customer_id,)
        )
        return Customer.from_row(row) if row else None

    def has_sales(self, customer_id: int) -> bool:
        row = self.db.query_one(
            "SELECT 1 FROM sales WHERE customer_id=? LIMIT 1", (customer_id,)
        )
        return row is not None

    def list_all(self, search: str = "") -> list[Customer]:
        if search.strip():
            like = f"%{search.strip()}%"
            rows = self.db.query(
                "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? "
                "OR national_id LIKE ? ORDER BY name",
                (like, like, like),
            )
        else:
            rows = self.db.query("SELECT * FROM customers ORDER BY name")
        return [Customer.from_row(r) for r in rows]

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS c FROM customers")
        return int(row["c"]) if row else 0
