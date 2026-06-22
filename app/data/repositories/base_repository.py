"""الأساس المشترك للمستودعات: يحمل مرجع قاعدة البيانات فقط.

المستودعات هي المكان الوحيد الذي يُكتب فيه SQL. لا تحتوي منطق عمل.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.data.database import Database


class BaseRepository:
    def __init__(self, db: "Database"):
        self.db = db

    @staticmethod
    def next_sequence(conn, name: str, prefix: str, width: int = 6) -> str:
        """يولّد الرقم التسلسلي التالي لتسلسل مُسمّى داخل معاملة مفتوحة.

        يُستخدم لترقيم الفواتير الرسمي بصيغة ``<prefix><رقم مصفوف بأصفار>``.
        """
        row = conn.execute(
            "SELECT value FROM number_sequences WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO number_sequences(name, value) VALUES (?, 0)", (name,)
            )
            value = 0
        else:
            value = row["value"]
        value += 1
        conn.execute(
            "UPDATE number_sequences SET value = ? WHERE name = ?", (value, name)
        )
        return f"{prefix}{value:0{width}d}"
