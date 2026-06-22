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
