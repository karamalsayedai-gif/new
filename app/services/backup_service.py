"""خدمة النسخ الاحتياطي والاستعادة.

- يدوي / تلقائي (حسب فترة) / عند إغلاق التطبيق.
- اختيار مسار وجهة للنسخة، أو المجلد الافتراضي داخل بيانات التطبيق.
- التحقق من سلامة النسخة (integrity_check + وجود الجداول الأساسية).
- نسخة أمان تلقائية قبل أي استعادة.
- تسجيل كل عملية في سجل التدقيق.
"""
from __future__ import annotations

import shutil
import sqlite3
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
    _REQUIRED_TABLES = ("users", "settings", "sales", "treasury")

    def __init__(
        self, db: Database, settings: SettingsService, audit: AuditService
    ):
        self._db = db
        self._settings = settings
        self._audit = audit

    # ── إنشاء ───────────────────────────────────────────────────────────
    def create_backup(
        self,
        user_id: int | None = None,
        dest_path: Path | str | None = None,
        *,
        label: str = "backup",
    ) -> Path:
        """ينشئ نسخة احتياطية. إن مُرِّر dest_path يُستخدم، وإلا المجلد الافتراضي."""
        if dest_path is not None:
            target = Path(dest_path)
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = AppConfig.backups_dir() / f"{label}_{stamp}.db"
        try:
            self._db.backup_to(target)
        except Exception as exc:  # noqa: BLE001
            raise BackupError(f"فشل إنشاء النسخة الاحتياطية: {exc}") from exc

        self._settings.set(SettingKeys.LAST_BACKUP_AT, now_iso())
        self._audit.log("backup_create", user_id=user_id, details=str(target))
        return target

    # ── التحقق ──────────────────────────────────────────────────────────
    def verify_backup(self, path: Path | str) -> tuple[bool, str]:
        """يتحقق من أن الملف قاعدة SQLite سليمة وتحوي الجداول الأساسية."""
        path = Path(path)
        if not path.exists():
            return False, "الملف غير موجود."
        try:
            con = sqlite3.connect(str(path))
            try:
                integrity = con.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    return False, "فحص السلامة فشل (الملف تالف)."
                names = {
                    r[0]
                    for r in con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                missing = [t for t in self._REQUIRED_TABLES if t not in names]
                if missing:
                    return False, f"جداول ناقصة: {', '.join(missing)}"
            finally:
                con.close()
        except sqlite3.Error as exc:
            return False, f"ليس ملف قاعدة بيانات صالحًا: {exc}"
        return True, "النسخة سليمة."

    # ── الاستعادة ───────────────────────────────────────────────────────
    def restore_backup(self, source: Path | str, user_id: int | None = None) -> None:
        """يتحقق من النسخة، يأخذ نسخة أمان من الحالية، ثم يستبدل الملف ويعيد الفتح."""
        source = Path(source)
        ok, message = self.verify_backup(source)
        if not ok:
            raise BackupError(f"النسخة غير صالحة: {message}")

        # نسخة أمان من قاعدة البيانات الحالية قبل الاستبدال.
        try:
            self.create_backup(user_id, label="pre_restore")
        except BackupError:
            pass

        db_path = AppConfig.database_path()
        self._db.close()
        try:
            shutil.copyfile(source, db_path)
        except Exception as exc:  # noqa: BLE001
            self._db.initialize()
            raise BackupError(f"فشل استعادة النسخة: {exc}") from exc
        self._db.initialize()

        self._settings.load()
        self._audit.log("backup_restore", user_id=user_id, details=str(source))

    # ── النسخ التلقائي وعند الإغلاق ──────────────────────────────────────
    def maybe_run_auto_backup(self) -> Path | None:
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
        return self.create_backup(label="auto")

    def run_backup_on_close(self) -> Path | None:
        if self._settings.get_bool(SettingKeys.BACKUP_ON_CLOSE):
            try:
                return self.create_backup(label="onclose")
            except BackupError:
                return None
        return None

    # ── قائمة النسخ ─────────────────────────────────────────────────────
    def list_backups(self) -> list[dict]:
        out: list[dict] = []
        for f in sorted(
            AppConfig.backups_dir().glob("*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            stat = f.stat()
            out.append(
                {
                    "path": f,
                    "name": f.name,
                    "size_kb": stat.st_size / 1024,
                    "mtime": datetime.fromtimestamp(stat.st_mtime),
                }
            )
        return out
