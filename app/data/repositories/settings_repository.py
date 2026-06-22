"""مستودع الإعدادات: قراءة/كتابة جدول settings."""
from __future__ import annotations

from app.data.repositories.base_repository import BaseRepository


class SettingsRepository(BaseRepository):
    def load_all(self) -> dict[str, str]:
        rows = self.db.query("SELECT key, value FROM settings")
        return {row["key"]: (row["value"] or "") for row in rows}

    def set(self, key: str, value: str, type_: str = "string") -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO settings(key, value, type) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "type = excluded.type",
                (key, value, type_),
            )

    def set_many(self, values: dict[str, str]) -> None:
        with self.db.transaction() as conn:
            conn.executemany(
                "INSERT INTO settings(key, value, type) VALUES (?, ?, 'string') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                list(values.items()),
            )
