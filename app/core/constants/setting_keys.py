"""مفاتيح الإعدادات وقيمها الافتراضية وأنواعها.

نظام الإعدادات بنمط key/value/type لجعل المنتج قابلاً للتخصيص لكل معرض دون
تعديل المخطط. كل مدخل افتراضي: (value, type).
"""
from __future__ import annotations


class SettingKeys:
    # بيانات المعرض
    SHOWROOM_NAME = "showroom_name"
    SHOWROOM_PHONE = "showroom_phone"
    SHOWROOM_ADDRESS = "showroom_address"

    # مالية
    CURRENCY_SYMBOL = "currency_symbol"
    DEFAULT_INTEREST_PCT = "default_interest_pct"

    # المظهر / القالب
    THEME_TEMPLATE = "theme_template"

    # النسخ الاحتياطي
    BACKUP_MODE = "backup_mode"  # manual | auto
    BACKUP_INTERVAL_DAYS = "backup_interval_days"
    BACKUP_ON_CLOSE = "backup_on_close"
    LAST_BACKUP_AT = "last_backup_at"

    # أمان الدخول
    LOGIN_MAX_ATTEMPTS = "login_max_attempts"
    LOGIN_LOCKOUT_MINUTES = "login_lockout_minutes"

    # ترقيم الفواتير الرسمي
    SALES_NO_PREFIX = "sales_no_prefix"
    PURCHASE_NO_PREFIX = "purchase_no_prefix"

    # قالب الطباعة القابل للتخصيص
    PRINT_HEADER = "print_header"
    PRINT_FOOTER = "print_footer"
    PRINT_SHOW_CONTACT = "print_show_contact"

    # حالة الإعداد لأول مرة
    SETUP_COMPLETED = "setup_completed"

    # key -> (default_value, type)
    DEFAULTS: dict[str, tuple[str, str]] = {
        SHOWROOM_NAME: ("معرضي", "string"),
        SHOWROOM_PHONE: ("", "string"),
        SHOWROOM_ADDRESS: ("", "string"),
        CURRENCY_SYMBOL: ("ج.م", "string"),
        DEFAULT_INTEREST_PCT: ("0", "double"),
        THEME_TEMPLATE: ("classic_business", "string"),
        BACKUP_MODE: ("manual", "string"),
        BACKUP_INTERVAL_DAYS: ("1", "int"),
        BACKUP_ON_CLOSE: ("false", "bool"),
        LAST_BACKUP_AT: ("", "string"),
        LOGIN_MAX_ATTEMPTS: ("5", "int"),
        LOGIN_LOCKOUT_MINUTES: ("15", "int"),
        SALES_NO_PREFIX: ("ف-", "string"),
        PURCHASE_NO_PREFIX: ("ش-", "string"),
        PRINT_HEADER: ("", "string"),
        PRINT_FOOTER: ("شكرًا لتعاملكم معنا", "string"),
        PRINT_SHOW_CONTACT: ("true", "bool"),
        SETUP_COMPLETED: ("false", "bool"),
    }
