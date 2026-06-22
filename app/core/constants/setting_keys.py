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
    LAST_BACKUP_AT = "last_backup_at"

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
        LAST_BACKUP_AT: ("", "string"),
        SETUP_COMPLETED: ("false", "bool"),
    }
