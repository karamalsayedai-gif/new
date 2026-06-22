"""شاشة الإعدادات: بيانات المعرض + تبديل القالب وقت التشغيل.

النسخ الاحتياطي والاستعادة في وحدتهما المستقلة. تُوسَّع الإعدادات لاحقًا لأقسام
أخرى (الفواتير، الأرقام التسلسلية، سياسات الأمان...).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.constants.permissions import Permissions
from app.core.constants.setting_keys import SettingKeys
from app.ui.components.widgets import Card, heading_label, muted_label, title_label

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
        layout.addWidget(
            muted_label("النسخ الاحتياطي والاستعادة في وحدة «النسخ الاحتياطي» المستقلة.")
        )
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
