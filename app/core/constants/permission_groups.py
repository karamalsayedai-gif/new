"""تجميع الصلاحيات حسب الوحدة لعرضها بشكل منظَّم في مصفوفة الأدوار."""
from __future__ import annotations

# بادئة الكود (module) -> اسم المجموعة بالعربية.
GROUP_LABELS: dict[str, str] = {
    "inventory": "المخزون",
    "suppliers": "الموردون",
    "purchases": "المشتريات",
    "customers": "العملاء",
    "sales_cash": "المبيعات النقدية",
    "sales_installment": "مبيعات التقسيط",
    "installments": "الأقساط",
    "treasury": "الخزينة",
    "expenses": "المصروفات والإيرادات",
    "reports": "التقارير",
    "day": "الإقفال اليومي",
    "users": "المستخدمون والأدوار",
    "settings": "الإعدادات",
    "backup": "النسخ الاحتياطي",
    "audit": "سجل التدقيق",
}


def group_of(code: str) -> str:
    return code.split(".", 1)[0]


def group_label(code: str) -> str:
    return GROUP_LABELS.get(group_of(code), group_of(code))
