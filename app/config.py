"""إعدادات ومسارات ثابتة على مستوى التطبيق.

- بيانات التشغيل (قاعدة البيانات + النسخ الاحتياطية) تُخزَّن في ``%LOCALAPPDATA%``
  حتى لا تُفقد عند التحديث ولا تتطلب صلاحيات كتابة في مجلد التثبيت.
- موارد القراءة فقط (القوالب، الأيقونات، الخطوط) تُحمَّل عبر مسار آمن للتغليف
  يدعم PyInstaller (``sys._MEIPASS``) ووضع التطوير على حدّ سواء.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_base() -> Path:
    """جذر الموارد المجمّعة (read-only) بشكل آمن للتغليف.

    - عند التجميد بـ PyInstaller: مجلد ``_MEIPASS`` المؤقت.
    - في وضع التطوير: جذر المستودع (المجلد الأب لحزمة ``app``).
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """بناء مسار مورد مجمّع آمن للتغليف."""
    return resource_base().joinpath(*parts)


class AppConfig:
    APP_NAME = "Showroom ERP"
    APP_NAME_AR = "نظام إدارة معرض الدراجات النارية"

    # إصدار مخطط قاعدة البيانات — يُزاد عند أي تغيير في الجداول (Migrations).
    DB_SCHEMA_VERSION = 9

    DEFAULT_THEME = "classic_business"

    _ROOT_FOLDER = "ShowroomERP"
    _DB_FILE = "showroom.db"
    _BACKUPS_FOLDER = "backups"

    @classmethod
    def data_dir(cls) -> Path:
        """المجلد الجذر القابل للكتابة لبيانات التطبيق (يُنشأ إن لم يوجد)."""
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = Path(base) / cls._ROOT_FOLDER
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def database_path(cls) -> Path:
        return cls.data_dir() / cls._DB_FILE

    @classmethod
    def backups_dir(cls) -> Path:
        path = cls.data_dir() / cls._BACKUPS_FOLDER
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def themes_dir(cls) -> Path:
        """مجلد قوالب الثيم (مورد قراءة فقط، آمن للتغليف)."""
        return resource_path("app", "theme", "themes")

    @classmethod
    def assets_dir(cls) -> Path:
        return resource_path("app", "assets")
