"""خرائط عربية لأكواد سجل التدقيق: العملية (التصنيف) والوحدة (الكيان).

تُستخدم في شاشة سجل التدقيق لعرض إداري مفهوم بدل الأكواد الخام.
"""
from __future__ import annotations

# كود الإجراء -> وصف عربي مفصّل.
ACTION_LABELS: dict[str, str] = {
    "login": "تسجيل دخول",
    "logout": "تسجيل خروج",
    "create_first_admin": "إنشاء مدير أوّلي",
    "user_create": "إضافة مستخدم",
    "user_activate": "تفعيل مستخدم",
    "user_deactivate": "تعطيل مستخدم",
    "user_reset_password": "تعيين كلمة مرور",
    "role_permissions_update": "تعديل صلاحيات دور",
    "customer_create": "إضافة عميل",
    "customer_update": "تعديل عميل",
    "customer_delete": "حذف عميل",
    "supplier_create": "إضافة مورّد",
    "supplier_update": "تعديل مورّد",
    "supplier_delete": "حذف مورّد",
    "item_create": "إضافة صنف",
    "item_update": "تعديل صنف",
    "item_delete": "حذف صنف",
    "stock_adjust": "حركة مخزون",
    "purchase_create": "ترحيل فاتورة شراء",
    "purchase_delete": "حذف فاتورة شراء",
    "sale_create": "ترحيل فاتورة بيع",
    "sale_delete": "حذف فاتورة بيع",
    "installment_create": "إنشاء عقد تقسيط",
    "installment_collect": "تحصيل قسط",
    "treasury_add": "حركة خزينة",
    "treasury_delete": "حذف حركة خزينة",
    "day_close": "إقفال يوم",
    "day_reopen": "إعادة فتح يوم",
    "backup_create": "إنشاء نسخة احتياطية",
    "backup_restore": "استعادة نسخة احتياطية",
}

# الكيان -> اسم الوحدة بالعربية.
ENTITY_LABELS: dict[str, str] = {
    "users": "المستخدمون",
    "roles": "الأدوار",
    "customers": "العملاء",
    "suppliers": "الموردون",
    "inventory_items": "المخزون",
    "purchases": "المشتريات",
    "sales": "المبيعات",
    "installment_plans": "التقسيط",
    "treasury": "الخزينة",
    "day_closings": "الإقفال اليومي",
}


def action_label(code: str) -> str:
    return ACTION_LABELS.get(code, code)


def entity_label(code: str | None) -> str:
    if not code:
        return "—"
    return ENTITY_LABELS.get(code, code)


def operation_category(code: str) -> str:
    """تصنيف العملية العام (إضافة/تعديل/حذف/تحصيل/...)."""
    if code in ("create_first_admin",) or code.endswith("_create"):
        return "إضافة"
    if code.endswith("_update"):
        return "تعديل"
    if code.endswith("_delete"):
        return "حذف"
    if code == "installment_collect":
        return "تحصيل"
    if code == "backup_restore":
        return "استعادة"
    if code == "backup_create":
        return "نسخ احتياطي"
    if code == "day_close":
        return "إقفال يوم"
    if code == "day_reopen":
        return "إعادة فتح"
    if code in ("login", "logout"):
        return "دخول/خروج"
    if code == "stock_adjust":
        return "حركة مخزون"
    if code in ("treasury_add", "treasury_delete"):
        return "حركة خزينة"
    if code in ("user_activate", "user_deactivate", "user_reset_password",
                "role_permissions_update"):
        return "إدارة مستخدمين"
    return "أخرى"


# قائمة التصنيفات العامة لاستخدامها في فلتر العملية.
OPERATION_CATEGORIES = [
    "إضافة", "تعديل", "حذف", "تحصيل", "حركة خزينة", "حركة مخزون",
    "إقفال يوم", "إعادة فتح", "نسخ احتياطي", "استعادة", "دخول/خروج",
    "إدارة مستخدمين", "أخرى",
]
