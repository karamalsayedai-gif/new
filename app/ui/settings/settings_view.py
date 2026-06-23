"""شاشة الإعدادات: بيانات المعرض + تبديل القالب وقت التشغيل.

النسخ الاحتياطي والاستعادة في وحدتهما المستقلة. تُوسَّع الإعدادات لاحقًا لأقسام
أخرى (الفواتير، الأرقام التسلسلية، سياسات الأمان...).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QComboBox,
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
from app.ui.components.widgets import (
    Card,
    heading_label,
    muted_label,
    scroll_area,
    title_label,
)

if TYPE_CHECKING:
    from app.core.container import Container


class SettingsView(QWidget):
    def __init__(self, container: "Container"):
        super().__init__()
        self._c = container
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 20)
        outer.setSpacing(12)
        outer.addWidget(title_label("الإعدادات"))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(14)
        layout.addWidget(self._company_card())
        layout.addWidget(self._theme_card())
        layout.addWidget(self._print_card())
        layout.addWidget(self._security_card())
        layout.addWidget(
            muted_label("النسخ الاحتياطي والاستعادة في وحدة «النسخ الاحتياطي» المستقلة.")
        )
        layout.addStretch(1)
        outer.addWidget(scroll_area(content), stretch=1)

    # ── قالب الطباعة ────────────────────────────────────────────────────
    def _print_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("قالب الطباعة"))
        s = self._c.settings
        self._print_header = QLineEdit(s.get(SettingKeys.PRINT_HEADER))
        self._print_header.setPlaceholderText("سطر ترويسة إضافي (اختياري)")
        self._print_footer = QLineEdit(s.get(SettingKeys.PRINT_FOOTER))
        lay.addWidget(QLabel("سطر الترويسة"))
        lay.addWidget(self._print_header)
        lay.addWidget(QLabel("سطر التذييل"))
        lay.addWidget(self._print_footer)
        save = QPushButton("حفظ قالب الطباعة")
        save.setEnabled(self._c.auth.can(Permissions.SETTINGS_MANAGE))
        save.clicked.connect(self._save_print)
        lay.addWidget(save)
        return card

    def _save_print(self) -> None:
        self._c.settings.set(SettingKeys.PRINT_HEADER, self._print_header.text().strip())
        self._c.settings.set(SettingKeys.PRINT_FOOTER, self._print_footer.text().strip())
        QMessageBox.information(self, "تم", "تم حفظ قالب الطباعة.")

    # ── الأمان وترقيم الفواتير ──────────────────────────────────────────
    def _security_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("الأمان وترقيم الفواتير"))
        s = self._c.settings

        row = QHBoxLayout()
        row.addWidget(QLabel("أقصى محاولات دخول"))
        self._max_attempts = QSpinBox()
        self._max_attempts.setRange(3, 20)
        self._max_attempts.setValue(s.get_int(SettingKeys.LOGIN_MAX_ATTEMPTS, 5))
        row.addWidget(self._max_attempts)
        row.addWidget(QLabel("مدة القفل (دقيقة)"))
        self._lockout = QSpinBox()
        self._lockout.setRange(1, 1440)
        self._lockout.setValue(s.get_int(SettingKeys.LOGIN_LOCKOUT_MINUTES, 15))
        row.addWidget(self._lockout)
        row.addStretch(1)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("بادئة فاتورة البيع"))
        self._sales_prefix = QLineEdit(s.get(SettingKeys.SALES_NO_PREFIX))
        self._sales_prefix.setFixedWidth(90)
        row2.addWidget(self._sales_prefix)
        row2.addWidget(QLabel("بادئة فاتورة الشراء"))
        self._purchase_prefix = QLineEdit(s.get(SettingKeys.PURCHASE_NO_PREFIX))
        self._purchase_prefix.setFixedWidth(90)
        row2.addWidget(self._purchase_prefix)
        row2.addStretch(1)
        lay.addLayout(row2)

        save = QPushButton("حفظ إعدادات الأمان والترقيم")
        save.setEnabled(self._c.auth.can(Permissions.SETTINGS_MANAGE))
        save.clicked.connect(self._save_security)
        lay.addWidget(save)
        return card

    def _save_security(self) -> None:
        self._c.settings.set(
            SettingKeys.LOGIN_MAX_ATTEMPTS, str(self._max_attempts.value()), "int"
        )
        self._c.settings.set(
            SettingKeys.LOGIN_LOCKOUT_MINUTES, str(self._lockout.value()), "int"
        )
        self._c.settings.set(
            SettingKeys.SALES_NO_PREFIX, self._sales_prefix.text().strip() or "ف-"
        )
        self._c.settings.set(
            SettingKeys.PURCHASE_NO_PREFIX,
            self._purchase_prefix.text().strip() or "ش-",
        )
        QMessageBox.information(self, "تم", "تم حفظ إعدادات الأمان والترقيم.")

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
