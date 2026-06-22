"""شاشة الإعدادات: بيانات المعرض + تبديل القالب وقت التشغيل + النسخ الاحتياطي.

هذه أساس المرحلة 2؛ تُوسَّع لاحقًا لبقية أقسام الإعدادات (الفواتير، التقسيط،
سياسات الأمان...).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.constants.setting_keys import SettingKeys
from app.services.backup_service import BackupError
from app.ui.components.widgets import Card, heading_label, title_label

if TYPE_CHECKING:
    from app.core.container import Container


class SettingsView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(title_label("الإعدادات"))

        layout.addWidget(self._company_card())
        layout.addWidget(self._theme_card())
        if self._c.auth.can(Permissions.BACKUP_MANAGE):
            layout.addWidget(self._backup_card())
        layout.addStretch(1)

    # ── بيانات المعرض ───────────────────────────────────────────────────
    def _company_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("بيانات المعرض"))

        s = self._c.settings
        self._name = QLineEdit(s.get(SettingKeys.SHOWROOM_NAME))
        self._phone = QLineEdit(s.get(SettingKeys.SHOWROOM_PHONE))
        self._address = QLineEdit(s.get(SettingKeys.SHOWROOM_ADDRESS))
        self._currency = QLineEdit(s.get(SettingKeys.CURRENCY_SYMBOL))

        lay.addWidget(QLabel("اسم المعرض"))
        lay.addWidget(self._name)
        lay.addWidget(QLabel("الهاتف"))
        lay.addWidget(self._phone)
        lay.addWidget(QLabel("العنوان"))
        lay.addWidget(self._address)
        lay.addWidget(QLabel("رمز العملة"))
        lay.addWidget(self._currency)

        save = QPushButton("حفظ بيانات المعرض")
        save.setEnabled(self._c.auth.can(Permissions.SETTINGS_MANAGE))
        save.clicked.connect(self._save_company)
        lay.addWidget(save)
        return card

    def _save_company(self) -> None:
        self._c.settings.set_many(
            {
                SettingKeys.SHOWROOM_NAME: self._name.text().strip(),
                SettingKeys.SHOWROOM_PHONE: self._phone.text().strip(),
                SettingKeys.SHOWROOM_ADDRESS: self._address.text().strip(),
                SettingKeys.CURRENCY_SYMBOL: self._currency.text().strip() or "ج.م",
            }
        )
        QMessageBox.information(self, "تم", "تم حفظ بيانات المعرض.")

    # ── القالب ──────────────────────────────────────────────────────────
    def _theme_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("مظهر التطبيق (القالب)"))
        lay.addWidget(QLabel("اختر القالب — يُطبَّق فورًا على كل الشاشات:"))

        self._theme_combo = QComboBox()
        themes = self._c.theme.available_themes() if self._c.theme else []
        current = self._c.settings.theme_template
        for index, meta in enumerate(themes):
            self._theme_combo.addItem(meta["name"], meta["id"])
            if meta["id"] == current:
                self._theme_combo.setCurrentIndex(index)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_change)
        lay.addWidget(self._theme_combo)
        return card

    def _on_theme_change(self) -> None:
        if self._c.theme is None:
            return
        theme_id = self._theme_combo.currentData()
        if theme_id:
            self._c.theme.apply(theme_id)

    # ── النسخ الاحتياطي ─────────────────────────────────────────────────
    def _backup_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("النسخ الاحتياطي والاستعادة"))

        s = self._c.settings
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("الوضع"))
        self._backup_mode = QComboBox()
        self._backup_mode.addItem("يدوي", "manual")
        self._backup_mode.addItem("تلقائي", "auto")
        self._backup_mode.setCurrentIndex(
            1 if s.get(SettingKeys.BACKUP_MODE) == "auto" else 0
        )
        mode_row.addWidget(self._backup_mode)

        mode_row.addWidget(QLabel("كل (أيام)"))
        self._interval = QSpinBox()
        self._interval.setRange(1, 90)
        self._interval.setValue(s.get_int(SettingKeys.BACKUP_INTERVAL_DAYS, 1))
        mode_row.addWidget(self._interval)
        mode_row.addStretch(1)
        lay.addLayout(mode_row)

        save_policy = QPushButton("حفظ سياسة النسخ")
        save_policy.clicked.connect(self._save_backup_policy)
        lay.addWidget(save_policy)

        buttons = QHBoxLayout()
        backup_now = QPushButton("نسخ احتياطي الآن")
        backup_now.clicked.connect(self._backup_now)
        restore = QPushButton("استعادة من ملف")
        restore.setObjectName("Danger")
        restore.clicked.connect(self._restore)
        buttons.addWidget(backup_now)
        buttons.addWidget(restore)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        return card

    def _save_backup_policy(self) -> None:
        self._c.settings.set(
            SettingKeys.BACKUP_MODE, self._backup_mode.currentData()
        )
        self._c.settings.set(
            SettingKeys.BACKUP_INTERVAL_DAYS, str(self._interval.value()), "int"
        )
        QMessageBox.information(self, "تم", "تم حفظ سياسة النسخ الاحتياطي.")

    def _backup_now(self) -> None:
        user = self._c.auth.current_user
        try:
            path = self._c.backup.create_backup(user.id if user else None)
        except BackupError as exc:
            QMessageBox.critical(self, "خطأ", str(exc))
            return
        QMessageBox.information(self, "تم", f"تم إنشاء النسخة الاحتياطية:\n{path}")

    def _restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف النسخة الاحتياطية", "", "قاعدة بيانات (*.db)"
        )
        if not path:
            return
        confirm = QMessageBox.question(
            self,
            "تأكيد الاستعادة",
            "سيتم استبدال البيانات الحالية بالكامل. هل أنت متأكد؟",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        user = self._c.auth.current_user
        try:
            self._c.backup.restore_backup(path, user.id if user else None)
        except BackupError as exc:
            QMessageBox.critical(self, "خطأ", str(exc))
            return
        QMessageBox.information(
            self,
            "تمت الاستعادة",
            "تمت استعادة البيانات. يُفضّل إعادة تشغيل البرنامج.",
        )
