"""خدمة النسخ الاحتياطي والاستعادة.

تدعم وضعين: يدوي وتلقائي (حسب فترة محدّدة في الإعدادات). تستخدم آلية النسخ
الآمنة في sqlite3 التي تتعامل مع المعاملات الجارية.
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.config import AppConfig
from app.core.constants.setting_keys import SettingKeys
from app.core.utils.formatters import now_iso
from app.data.database import Database
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService


class BackupError(Exception):
    """خطأ في النسخ الاحتياطي/الاستعادة مع رسالة عربية."""


class BackupService:
    def __init__(
        self,
        db: Database,
        settings: SettingsService,
        audit: AuditService,
    ):
        self._db = db
        self._settings = settings
        self._audit = audit

    def create_backup(self, user_id: int | None = None) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = AppConfig.backups_dir() / f"backup_{stamp}.db"
        try:
            self._db.backup_to(target)
        except Exception as exc:  # noqa: BLE001
            raise BackupError(f"فشل إنشاء النسخة الاحتياطية: {exc}") from exc

        self._settings.set(SettingKeys.LAST_BACKUP_AT, now_iso())
        self._audit.log("backup_create", user_id=user_id, details=str(target))
        return target

    def restore_backup(self, source: Path | str, user_id: int | None = None) -> None:
        """استعادة من ملف: تُغلق قاعدة البيانات ويُستبدل الملف ثم يُعاد فتحه."""
        source = Path(source)
        if not source.exists():
            raise BackupError("ملف النسخة الاحتياطية غير موجود.")

        db_path = AppConfig.database_path()
        self._db.close()
        try:
            shutil.copyfile(source, db_path)
        except Exception as exc:  # noqa: BLE001
            raise BackupError(f"فشل استعادة النسخة: {exc}") from exc
        finally:
            self._db.initialize()

        self._settings.load()
        self._audit.log("backup_restore", user_id=user_id, details=str(source))

    def maybe_run_auto_backup(self) -> Path | None:
        """ينفّذ نسخة تلقائية إذا كان الوضع 'auto' وانقضت الفترة المحددة."""
        if self._settings.get(SettingKeys.BACKUP_MODE) != "auto":
            return None
        interval_days = self._settings.get_int(SettingKeys.BACKUP_INTERVAL_DAYS, 1)
        last_raw = self._settings.get(SettingKeys.LAST_BACKUP_AT)
        if last_raw:
            try:
                last = datetime.fromisoformat(last_raw)
                if (datetime.now() - last).days < max(interval_days, 1):
                    return None
            except ValueError:
                pass
        return self.create_backup()
