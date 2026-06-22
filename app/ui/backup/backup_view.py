"""وحدة النسخ الاحتياطي والاستعادة — شاشة كاملة.

تشمل: سياسة النسخ (يدوي/تلقائي/عند الإغلاق)، نسخ الآن، نسخ إلى مسار، قائمة
النسخ، التحقق من سلامة نسخة، والاستعادة (مع نسخة أمان تلقائية قبلها).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.constants.setting_keys import SettingKeys
from app.core.utils.formatters import format_datetime
from app.services.backup_service import BackupError
from app.ui.components.widgets import Card, heading_label, muted_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


class BackupView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._can = container.auth.can(Permissions.BACKUP_MANAGE)
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 26)
        layout.setSpacing(14)
        layout.addWidget(title_label("النسخ الاحتياطي والاستعادة"))
        if not self._can:
            layout.addWidget(muted_label("لا تملك صلاحية إدارة النسخ الاحتياطي."))
        layout.addWidget(self._policy_card())
        layout.addWidget(self._actions_card())
        layout.addWidget(heading_label("النسخ المتاحة"))
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["الملف", "الحجم (ك.ب)", "التاريخ"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table, stretch=1)

        row = QHBoxLayout()
        row.addStretch(1)
        restore_sel = QPushButton("استعادة المحدد")
        restore_sel.setObjectName("Danger")
        restore_sel.setEnabled(self._can)
        restore_sel.clicked.connect(self._restore_selected)
        verify_sel = QPushButton("تحقّق المحدد")
        verify_sel.setObjectName("Ghost")
        verify_sel.clicked.connect(self._verify_selected)
        row.addWidget(verify_sel)
        row.addWidget(restore_sel)
        layout.addLayout(row)

    def _policy_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("سياسة النسخ"))
        s = self._c.settings
        row = QHBoxLayout()
        row.addWidget(QLabel("الوضع"))
        self._mode = QComboBox()
        self._mode.addItem("يدوي", "manual")
        self._mode.addItem("تلقائي", "auto")
        self._mode.setCurrentIndex(1 if s.get(SettingKeys.BACKUP_MODE) == "auto" else 0)
        row.addWidget(self._mode)
        row.addWidget(QLabel("كل (أيام)"))
        self._interval = QSpinBox()
        self._interval.setRange(1, 90)
        self._interval.setValue(s.get_int(SettingKeys.BACKUP_INTERVAL_DAYS, 1))
        row.addWidget(self._interval)
        self._on_close = QCheckBox("نسخة عند إغلاق البرنامج")
        self._on_close.setChecked(s.get_bool(SettingKeys.BACKUP_ON_CLOSE))
        row.addWidget(self._on_close)
        row.addStretch(1)
        lay.addLayout(row)
        save = QPushButton("حفظ السياسة")
        save.setEnabled(self._can)
        save.clicked.connect(self._save_policy)
        lay.addWidget(save)
        return card

    def _actions_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("إجراءات"))
        row = QHBoxLayout()
        now = QPushButton("نسخ احتياطي الآن")
        now.setEnabled(self._can)
        now.clicked.connect(self._backup_now)
        to_path = QPushButton("نسخ إلى مسار…")
        to_path.setEnabled(self._can)
        to_path.clicked.connect(self._backup_to_path)
        from_file = QPushButton("استعادة من ملف…")
        from_file.setObjectName("Danger")
        from_file.setEnabled(self._can)
        from_file.clicked.connect(self._restore_from_file)
        verify = QPushButton("التحقق من نسخة…")
        verify.setObjectName("Ghost")
        verify.clicked.connect(self._verify_file)
        for b in (now, to_path, from_file, verify):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        return card

    # ── بيانات ──────────────────────────────────────────────────────────
    def refresh(self) -> None:
        backups = self._c.backup.list_backups()
        self._table.setRowCount(len(backups))
        for r, b in enumerate(backups):
            name_item = QTableWidgetItem(b["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, str(b["path"]))
            self._table.setItem(r, 0, name_item)
            self._table.setItem(r, 1, QTableWidgetItem(f"{b['size_kb']:.1f}"))
            self._table.setItem(r, 2, QTableWidgetItem(format_datetime(b["mtime"])))

    def _selected_path(self) -> str | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _actor_id(self) -> int | None:
        user = self._c.auth.current_user
        return user.id if user else None

    # ── أفعال ───────────────────────────────────────────────────────────
    def _save_policy(self) -> None:
        self._c.settings.set(SettingKeys.BACKUP_MODE, self._mode.currentData())
        self._c.settings.set(
            SettingKeys.BACKUP_INTERVAL_DAYS, str(self._interval.value()), "int"
        )
        self._c.settings.set(
            SettingKeys.BACKUP_ON_CLOSE,
            "true" if self._on_close.isChecked() else "false", "bool",
        )
        QMessageBox.information(self, "تم", "تم حفظ سياسة النسخ.")

    def _backup_now(self) -> None:
        try:
            path = self._c.backup.create_backup(self._actor_id())
        except BackupError as exc:
            QMessageBox.critical(self, "خطأ", str(exc))
            return
        QMessageBox.information(self, "تم", f"تم إنشاء النسخة:\n{path}")
        self.refresh()

    def _backup_to_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ نسخة احتياطية", "showroom_backup.db", "قاعدة بيانات (*.db)"
        )
        if not path:
            return
        try:
            self._c.backup.create_backup(self._actor_id(), dest_path=path)
        except BackupError as exc:
            QMessageBox.critical(self, "خطأ", str(exc))
            return
        QMessageBox.information(self, "تم", f"تم حفظ النسخة:\n{path}")
        self.refresh()

    def _verify_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "اختر نسخة للتحقق", "", "قاعدة بيانات (*.db)"
        )
        if path:
            self._show_verify(path)

    def _verify_selected(self) -> None:
        path = self._selected_path()
        if path is None:
            QMessageBox.information(self, "تنبيه", "اختر نسخة أولًا.")
            return
        self._show_verify(path)

    def _show_verify(self, path: str) -> None:
        ok, message = self._c.backup.verify_backup(path)
        if ok:
            QMessageBox.information(self, "تحقق", message)
        else:
            QMessageBox.warning(self, "تحقق", message)

    def _restore_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "اختر نسخة للاستعادة", "", "قاعدة بيانات (*.db)"
        )
        if path:
            self._do_restore(path)

    def _restore_selected(self) -> None:
        path = self._selected_path()
        if path is None:
            QMessageBox.information(self, "تنبيه", "اختر نسخة أولًا.")
            return
        self._do_restore(path)

    def _do_restore(self, path: str) -> None:
        confirm = QMessageBox.question(
            self, "تأكيد الاستعادة",
            "سيتم أخذ نسخة أمان من البيانات الحالية ثم استبدالها بالكامل. متابعة؟",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self._c.backup.restore_backup(path, self._actor_id())
        except BackupError as exc:
            QMessageBox.critical(self, "خطأ", str(exc))
            return
        QMessageBox.information(
            self, "تمت الاستعادة",
            "تمت استعادة البيانات بنجاح. يُفضّل إعادة تشغيل البرنامج.",
        )
        self.refresh()
