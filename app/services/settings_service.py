"""خدمة الإعدادات: تحميل القيم في الذاكرة وتوفير قراءة/كتابة مكتوبة النوع."""
from __future__ import annotations

from app.core.constants.setting_keys import SettingKeys
from app.data.repositories.settings_repository import SettingsRepository


class SettingsService:
    def __init__(self, repo: SettingsRepository):
        self._repo = repo
        self._cache: dict[str, str] = {}

    def load(self) -> None:
        self._cache = self._repo.load_all()

    # ── قراءة ───────────────────────────────────────────────────────────
    def get(self, key: str, default: str | None = None) -> str:
        if key in self._cache:
            return self._cache[key]
        if default is not None:
            return default
        fallback = SettingKeys.DEFAULTS.get(key)
        return fallback[0] if fallback else ""

    def get_bool(self, key: str) -> bool:
        return self.get(key).strip().lower() == "true"

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key))
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get(key))
        except (ValueError, TypeError):
            return default

    # ── كتابة ───────────────────────────────────────────────────────────
    def set(self, key: str, value: str, type_: str = "string") -> None:
        self._repo.set(key, value, type_)
        self._cache[key] = value

    def set_many(self, values: dict[str, str]) -> None:
        self._repo.set_many(values)
        self._cache.update(values)

    def mark_setup_completed(self) -> None:
        self.set(SettingKeys.SETUP_COMPLETED, "true", "bool")

    # ── اختصارات شائعة ──────────────────────────────────────────────────
    @property
    def is_setup_completed(self) -> bool:
        return self.get_bool(SettingKeys.SETUP_COMPLETED)

    @property
    def theme_template(self) -> str:
        return self.get(SettingKeys.THEME_TEMPLATE)

    @property
    def currency_symbol(self) -> str:
        return self.get(SettingKeys.CURRENCY_SYMBOL)

    @property
    def showroom_name(self) -> str:
        return self.get(SettingKeys.SHOWROOM_NAME)
