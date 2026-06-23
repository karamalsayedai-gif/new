"""شاشة الإعدادات الشاملة: بيانات المعرض، المظهر والقالب، تخصيص الألوان،
الطباعة، المخزون، الضريبة، التقسيط، النسخ الاحتياطي، والأمان وترقيم الفواتير.

كل قسم في بطاقة مستقلة، والكل داخل منطقة تمرير. تخصيص الألوان يطبّق فورًا على
كامل النظام عبر ThemeManager.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

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
        self._can = container.auth.can(Permissions.SETTINGS_MANAGE)
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 20)
        outer.setSpacing(12)
        outer.addWidget(title_label("الإعدادات"))
        outer.addWidget(
            muted_label("اضبط كل تفاصيل النظام — كل قسم يُحفظ على حدة.")
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(14)
        layout.addWidget(self._company_card())
        layout.addWidget(self._theme_card())
        layout.addWidget(self._colors_card())
        layout.addWidget(self._inventory_card())
        layout.addWidget(self._tax_card())
        layout.addWidget(self._installment_card())
        layout.addWidget(self._print_card())
        layout.addWidget(self._backup_card())
        layout.addWidget(self._security_card())
        layout.addWidget(
            muted_label(
                "النسخ الاحتياطي والاستعادة الفعلية في وحدة «النسخ الاحتياطي» المستقلة."
            )
        )
        layout.addStretch(1)
        outer.addWidget(scroll_area(content), stretch=1)

    # ── بيانات المعرض ───────────────────────────────────────────────────
    def _company_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("🏪  بيانات المعرض"))
        s = self._c.settings
        self._name = QLineEdit(s.get(SettingKeys.SHOWROOM_NAME))
        self._phone = QLineEdit(s.get(SettingKeys.SHOWROOM_PHONE))
        self._address = QLineEdit(s.get(SettingKeys.SHOWROOM_ADDRESS))
        self._currency = QLineEdit(s.get(SettingKeys.CURRENCY_SYMBOL))
        for label, widget in (
            ("اسم المعرض", self._name),
            ("الهاتف", self._phone),
            ("العنوان", self._address),
            ("رمز العملة", self._currency),
        ):
            lay.addWidget(QLabel(label))
            lay.addWidget(widget)

        logo_row = QHBoxLayout()
        self._logo = QLineEdit(s.get(SettingKeys.SHOWROOM_LOGO))
        self._logo.setPlaceholderText("مسار صورة الشعار (تظهر على الطباعة)")
        pick = QPushButton("اختيار…")
        pick.setObjectName("Ghost")
        pick.clicked.connect(self._pick_logo)
        logo_row.addWidget(QLabel("الشعار"))
        logo_row.addWidget(self._logo, stretch=1)
        logo_row.addWidget(pick)
        lay.addLayout(logo_row)

        lay.addWidget(self._save_button("حفظ بيانات المعرض", self._save_company))
        return card

    def _pick_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "اختر صورة الشعار", "", "صور (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._logo.setText(path)

    def _save_company(self) -> None:
        self._c.settings.set_many(
            {
                SettingKeys.SHOWROOM_NAME: self._name.text().strip(),
                SettingKeys.SHOWROOM_PHONE: self._phone.text().strip(),
                SettingKeys.SHOWROOM_ADDRESS: self._address.text().strip(),
                SettingKeys.CURRENCY_SYMBOL: self._currency.text().strip() or "ج.م",
                SettingKeys.SHOWROOM_LOGO: self._logo.text().strip(),
            }
        )
        self._done("تم حفظ بيانات المعرض.")

    # ── القالب ──────────────────────────────────────────────────────────
    def _theme_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("🎨  مظهر التطبيق (القالب)"))
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

    # ── تخصيص الألوان ───────────────────────────────────────────────────
    def _colors_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("🌈  تخصيص الألوان"))
        lay.addWidget(
            muted_label("اختر لونك الخاص ودرجته — يُطبَّق فورًا ويُحفظ تلقائيًا.")
        )
        s = self._c.settings
        self._primary_hex = s.get(SettingKeys.THEME_PRIMARY) or self._tok("primary", "#1D4ED8")
        self._accent_hex = s.get(SettingKeys.THEME_ACCENT) or self._tok("accent", "#06B6D4")

        row = QHBoxLayout()
        self._primary_btn = self._color_button(self._primary_hex)
        self._primary_btn.clicked.connect(self._pick_primary)
        self._accent_btn = self._color_button(self._accent_hex)
        self._accent_btn.clicked.connect(self._pick_accent)
        row.addWidget(QLabel("اللون الأساسي"))
        row.addWidget(self._primary_btn)
        row.addSpacing(18)
        row.addWidget(QLabel("لون التمييز"))
        row.addWidget(self._accent_btn)
        row.addStretch(1)
        lay.addLayout(row)

        shade_row = QHBoxLayout()
        shade_row.addWidget(QLabel("الدرجة (غامق ← → فاتح)"))
        self._shade = QSlider(Qt.Orientation.Horizontal)
        self._shade.setRange(-100, 100)
        self._shade.setValue(s.get_int(SettingKeys.THEME_SHADE, 0))
        self._shade.setEnabled(self._can)
        self._shade.sliderReleased.connect(self._apply_colors)
        shade_row.addWidget(self._shade, stretch=1)
        lay.addLayout(shade_row)

        btns = QHBoxLayout()
        apply_btn = QPushButton("تطبيق الألوان")
        apply_btn.setEnabled(self._can)
        apply_btn.clicked.connect(self._apply_colors)
        reset = QPushButton("استرجاع ألوان القالب")
        reset.setObjectName("Ghost")
        reset.setEnabled(self._can)
        reset.clicked.connect(self._reset_colors)
        btns.addWidget(apply_btn)
        btns.addWidget(reset)
        btns.addStretch(1)
        lay.addLayout(btns)
        return card

    def _tok(self, name: str, fallback: str) -> str:
        return (self._c.theme.token(name) if self._c.theme else "") or fallback

    @staticmethod
    def _color_button(hex_value: str) -> QPushButton:
        btn = QPushButton(hex_value)
        btn.setObjectName("Ghost")
        btn.setFixedWidth(120)
        SettingsView._paint_swatch(btn, hex_value)
        return btn

    @staticmethod
    def _paint_swatch(btn: QPushButton, hex_value: str) -> None:
        text_color = "#FFFFFF" if QColor(hex_value).lightnessF() < 0.6 else "#16202E"
        btn.setText(hex_value)
        btn.setStyleSheet(
            f"background:{hex_value}; color:{text_color}; border:1px solid rgba(0,0,0,0.2);"
            "border-radius:8px; padding:8px 10px; font-weight:700;"
        )

    def _pick_primary(self) -> None:
        col = QColorDialog.getColor(QColor(self._primary_hex), self, "اللون الأساسي")
        if col.isValid():
            self._primary_hex = col.name().upper()
            self._paint_swatch(self._primary_btn, self._primary_hex)
            self._apply_colors()

    def _pick_accent(self) -> None:
        col = QColorDialog.getColor(QColor(self._accent_hex), self, "لون التمييز")
        if col.isValid():
            self._accent_hex = col.name().upper()
            self._paint_swatch(self._accent_btn, self._accent_hex)
            self._apply_colors()

    def _apply_colors(self) -> None:
        if self._c.theme is None or not self._can:
            return
        self._c.theme.set_color_overrides(
            primary=self._primary_hex,
            accent=self._accent_hex,
            shade=self._shade.value(),
        )

    def _reset_colors(self) -> None:
        if self._c.theme is None:
            return
        self._c.theme.reset_color_overrides()
        self._primary_hex = self._tok("primary", "#1D4ED8")
        self._accent_hex = self._tok("accent", "#06B6D4")
        self._paint_swatch(self._primary_btn, self._primary_hex)
        self._paint_swatch(self._accent_btn, self._accent_hex)
        self._shade.setValue(0)

    # ── المخزون ─────────────────────────────────────────────────────────
    def _inventory_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("📦  المخزون"))
        s = self._c.settings
        row = QHBoxLayout()
        row.addWidget(QLabel("حد التنبيه للأصناف الناقصة"))
        self._low_stock = QSpinBox()
        self._low_stock.setRange(0, 1000)
        self._low_stock.setValue(s.get_int(SettingKeys.LOW_STOCK_THRESHOLD, 3))
        row.addWidget(self._low_stock)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(self._save_button("حفظ إعدادات المخزون", self._save_inventory))
        return card

    def _save_inventory(self) -> None:
        self._c.settings.set(
            SettingKeys.LOW_STOCK_THRESHOLD, str(self._low_stock.value()), "int"
        )
        self._done("تم حفظ إعدادات المخزون.")

    # ── الضريبة ─────────────────────────────────────────────────────────
    def _tax_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("🧾  الضريبة"))
        s = self._c.settings
        self._tax_enabled = QCheckBox("تفعيل الضريبة على الفواتير")
        self._tax_enabled.setChecked(s.get_bool(SettingKeys.TAX_ENABLED))
        lay.addWidget(self._tax_enabled)
        row = QHBoxLayout()
        row.addWidget(QLabel("نسبة الضريبة %"))
        self._tax_pct = QDoubleSpinBox()
        self._tax_pct.setRange(0, 100)
        self._tax_pct.setDecimals(2)
        self._tax_pct.setValue(s.get_float(SettingKeys.TAX_PERCENT, 0))
        row.addWidget(self._tax_pct)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(self._save_button("حفظ إعدادات الضريبة", self._save_tax))
        return card

    def _save_tax(self) -> None:
        self._c.settings.set(
            SettingKeys.TAX_ENABLED, "true" if self._tax_enabled.isChecked() else "false", "bool"
        )
        self._c.settings.set(
            SettingKeys.TAX_PERCENT, str(self._tax_pct.value()), "double"
        )
        self._done("تم حفظ إعدادات الضريبة.")

    # ── التقسيط ─────────────────────────────────────────────────────────
    def _installment_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("💳  التقسيط"))
        s = self._c.settings
        row = QHBoxLayout()
        row.addWidget(QLabel("عدد الأقساط الافتراضي"))
        self._inst_count = QSpinBox()
        self._inst_count.setRange(1, 120)
        self._inst_count.setValue(s.get_int(SettingKeys.DEFAULT_INSTALLMENT_COUNT, 6))
        row.addWidget(self._inst_count)
        row.addWidget(QLabel("نسبة الفائدة الافتراضية %"))
        self._inst_interest = QDoubleSpinBox()
        self._inst_interest.setRange(0, 100)
        self._inst_interest.setDecimals(2)
        self._inst_interest.setValue(s.get_float(SettingKeys.DEFAULT_INTEREST_PCT, 0))
        row.addWidget(self._inst_interest)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(self._save_button("حفظ إعدادات التقسيط", self._save_installment))
        return card

    def _save_installment(self) -> None:
        self._c.settings.set(
            SettingKeys.DEFAULT_INSTALLMENT_COUNT, str(self._inst_count.value()), "int"
        )
        self._c.settings.set(
            SettingKeys.DEFAULT_INTEREST_PCT, str(self._inst_interest.value()), "double"
        )
        self._done("تم حفظ إعدادات التقسيط.")

    # ── قالب الطباعة ────────────────────────────────────────────────────
    def _print_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("🖨️  قالب الطباعة"))
        s = self._c.settings
        self._print_header = QLineEdit(s.get(SettingKeys.PRINT_HEADER))
        self._print_header.setPlaceholderText("سطر ترويسة إضافي (اختياري)")
        self._print_footer = QLineEdit(s.get(SettingKeys.PRINT_FOOTER))
        lay.addWidget(QLabel("سطر الترويسة"))
        lay.addWidget(self._print_header)
        lay.addWidget(QLabel("سطر التذييل"))
        lay.addWidget(self._print_footer)
        self._print_contact = QCheckBox("إظهار بيانات التواصل على الطباعة")
        self._print_contact.setChecked(s.get_bool(SettingKeys.PRINT_SHOW_CONTACT))
        lay.addWidget(self._print_contact)
        lay.addWidget(self._save_button("حفظ قالب الطباعة", self._save_print))
        return card

    def _save_print(self) -> None:
        self._c.settings.set(SettingKeys.PRINT_HEADER, self._print_header.text().strip())
        self._c.settings.set(SettingKeys.PRINT_FOOTER, self._print_footer.text().strip())
        self._c.settings.set(
            SettingKeys.PRINT_SHOW_CONTACT,
            "true" if self._print_contact.isChecked() else "false",
            "bool",
        )
        self._done("تم حفظ قالب الطباعة.")

    # ── النسخ الاحتياطي ─────────────────────────────────────────────────
    def _backup_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("💾  النسخ الاحتياطي"))
        s = self._c.settings
        self._backup_on_close = QCheckBox("إنشاء نسخة احتياطية تلقائيًا عند إقفال اليوم")
        self._backup_on_close.setChecked(s.get_bool(SettingKeys.BACKUP_ON_CLOSE))
        lay.addWidget(self._backup_on_close)
        row = QHBoxLayout()
        row.addWidget(QLabel("التكرار (أيام)"))
        self._backup_interval = QSpinBox()
        self._backup_interval.setRange(1, 90)
        self._backup_interval.setValue(s.get_int(SettingKeys.BACKUP_INTERVAL_DAYS, 1))
        row.addWidget(self._backup_interval)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(self._save_button("حفظ إعدادات النسخ الاحتياطي", self._save_backup))
        return card

    def _save_backup(self) -> None:
        self._c.settings.set(
            SettingKeys.BACKUP_ON_CLOSE,
            "true" if self._backup_on_close.isChecked() else "false",
            "bool",
        )
        self._c.settings.set(
            SettingKeys.BACKUP_INTERVAL_DAYS, str(self._backup_interval.value()), "int"
        )
        self._done("تم حفظ إعدادات النسخ الاحتياطي.")

    # ── الأمان وترقيم الفواتير ──────────────────────────────────────────
    def _security_card(self) -> Card:
        card = Card()
        lay = card.layout()
        lay.addWidget(heading_label("🔐  الأمان وترقيم الفواتير"))
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
        lay.addWidget(
            self._save_button("حفظ إعدادات الأمان والترقيم", self._save_security)
        )
        return card

    def _save_security(self) -> None:
        s = self._c.settings
        s.set(SettingKeys.LOGIN_MAX_ATTEMPTS, str(self._max_attempts.value()), "int")
        s.set(SettingKeys.LOGIN_LOCKOUT_MINUTES, str(self._lockout.value()), "int")
        s.set(SettingKeys.SALES_NO_PREFIX, self._sales_prefix.text().strip() or "ف-")
        s.set(SettingKeys.PURCHASE_NO_PREFIX, self._purchase_prefix.text().strip() or "ش-")
        self._done("تم حفظ إعدادات الأمان والترقيم.")

    # ── أدوات مشتركة ────────────────────────────────────────────────────
    def _save_button(self, text: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setEnabled(self._can)
        btn.clicked.connect(slot)
        return btn

    def _done(self, message: str) -> None:
        QMessageBox.information(self, "تم", message)
