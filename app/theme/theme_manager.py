"""مدير القوالب المركزي.

مسؤول عن اكتشاف القوالب وتحميل أصولها وتطبيق QSS **عالميًا** على مستوى
``QApplication`` (وليس widget-by-widget)، ويبثّ إشارة عند التغيير لتعيد الشاشات
قراءة تلميحات التخطيط. تغيير القالب من الإعدادات يستدعي ``apply`` فيُعاد تنسيق
كل الشاشات فورًا.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from app.config import AppConfig
from app.core.constants.setting_keys import SettingKeys
from app.services.settings_service import SettingsService
from app.theme import qss_loader


class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)  # يحمل معرّف القالب الجديد

    def __init__(self, app: QApplication, settings: SettingsService):
        super().__init__()
        self._app = app
        self._settings = settings
        self._themes_dir = AppConfig.themes_dir()
        self._current: qss_loader.ThemeData | None = None

    # ── الاكتشاف ────────────────────────────────────────────────────────
    def available_themes(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if not self._themes_dir.exists():
            return result
        for child in sorted(self._themes_dir.iterdir()):
            if (child / qss_loader.MANIFEST).exists():
                try:
                    manifest = qss_loader.read_manifest(child)
                    result.append(
                        {
                            "id": manifest.get("id", child.name),
                            "name": manifest.get("name", child.name),
                            "mode": manifest.get("mode", "light"),
                        }
                    )
                except (ValueError, OSError):
                    continue
        return result

    # ── التطبيق ─────────────────────────────────────────────────────────
    def apply(self, theme_id: str, *, persist: bool = True) -> None:
        theme_dir = self._resolve_dir(theme_id)
        data = qss_loader.load_theme(theme_dir)
        self._current = data
        # تطبيق عالمي على كامل التطبيق.
        self._app.setStyleSheet(data.qss)
        if persist:
            self._settings.set(SettingKeys.THEME_TEMPLATE, data.id)
        self.theme_changed.emit(data.id)

    def apply_current(self) -> None:
        """تطبيق القالب المحفوظ في الإعدادات عند الإقلاع."""
        self.apply(self._settings.theme_template, persist=False)

    # ── استعلامات ───────────────────────────────────────────────────────
    @property
    def current_id(self) -> str:
        return self._current.id if self._current else ""

    @property
    def current_mode(self) -> str:
        return self._current.mode if self._current else "light"

    def layout_hint(self, key: str, default: Any = None) -> Any:
        if self._current is None:
            return default
        return self._current.layout.get(key, default)

    def token(self, name: str, default: str = "") -> str:
        if self._current is None:
            return default
        return self._current.tokens.get(name, default)

    # ── داخلي ───────────────────────────────────────────────────────────
    def _resolve_dir(self, theme_id: str) -> Path:
        candidate = self._themes_dir / theme_id
        if (candidate / qss_loader.MANIFEST).exists():
            return candidate
        fallback = self._themes_dir / AppConfig.DEFAULT_THEME
        if (fallback / qss_loader.MANIFEST).exists():
            return fallback
        raise FileNotFoundError(f"لا يوجد قالب بالمعرّف: {theme_id}")
