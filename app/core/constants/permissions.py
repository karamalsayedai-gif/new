"""كتالوج صلاحيات النظام (RBAC).

كل صلاحية لها كود نصّي ثابت بصيغة ``module.action``. تُخزَّن في جدول
``permissions`` ويُربط بها الدور عبر ``role_permissions``. أي وحدة جديدة تضيف
أكوادها هنا فقط، فيبقى هذا الملف المصدر الوحيد للحقيقة.
"""
from __future__ import annotations


class Permissions:
    # المخزون
    INVENTORY_VIEW = "inventory.view"
    INVENTORY_MANAGE = "inventory.manage"

    # الموردون والمشتريات
    SUPPLIERS_VIEW = "suppliers.view"
    SUPPLIERS_MANAGE = "suppliers.manage"
    PURCHASES_VIEW = "purchases.view"
    PURCHASES_MANAGE = "purchases.manage"

    # العملاء
    CUSTOMERS_VIEW = "customers.view"
    CUSTOMERS_MANAGE = "customers.manage"

    # المبيعات النقدية
    SALES_CASH_VIEW = "sales_cash.view"
    SALES_CASH_CREATE = "sales_cash.create"

    # مبيعات التقسيط
    SALES_INSTALLMENT_VIEW = "sales_installment.view"
    SALES_INSTALLMENT_CREATE = "sales_installment.create"
    INSTALLMENTS_COLLECT = "installments.collect"

    # الخزينة
    TREASURY_VIEW = "treasury.view"
    TREASURY_MANAGE = "treasury.manage"

    # المصروفات والإيرادات
    EXPENSES_VIEW = "expenses.view"
    EXPENSES_MANAGE = "expenses.manage"

    # التقارير
    REPORTS_VIEW = "reports.view"

    # الإقفال اليومي
    DAY_CLOSE = "day.close"
    DAY_REOPEN = "day.reopen"

    # المستخدمون والأدوار
    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"

    # الإعدادات
    SETTINGS_VIEW = "settings.view"
    SETTINGS_MANAGE = "settings.manage"

    # النسخ الاحتياطي
    BACKUP_MANAGE = "backup.manage"

    # سجل التدقيق
    AUDIT_VIEW = "audit.view"

    # الكود -> وصف عربي للعرض في شاشة إدارة الأدوار.
    CATALOG: dict[str, str] = {
        INVENTORY_VIEW: "عرض المخزون",
        INVENTORY_MANAGE: "إدارة المخزون",
        SUPPLIERS_VIEW: "عرض الموردين",
        SUPPLIERS_MANAGE: "إدارة الموردين",
        PURCHASES_VIEW: "عرض المشتريات",
        PURCHASES_MANAGE: "إدارة المشتريات",
        CUSTOMERS_VIEW: "عرض العملاء",
        CUSTOMERS_MANAGE: "إدارة العملاء",
        SALES_CASH_VIEW: "عرض المبيعات النقدية",
        SALES_CASH_CREATE: "إنشاء بيع نقدي",
        SALES_INSTALLMENT_VIEW: "عرض مبيعات التقسيط",
        SALES_INSTALLMENT_CREATE: "إنشاء بيع بالتقسيط",
        INSTALLMENTS_COLLECT: "تحصيل الأقساط",
        TREASURY_VIEW: "عرض الخزينة",
        TREASURY_MANAGE: "إدارة الخزينة",
        EXPENSES_VIEW: "عرض المصروفات والإيرادات",
        EXPENSES_MANAGE: "إدارة المصروفات والإيرادات",
        REPORTS_VIEW: "عرض التقارير",
        DAY_CLOSE: "تنفيذ الإقفال اليومي",
        DAY_REOPEN: "إعادة فتح يوم مُقفل",
        USERS_VIEW: "عرض المستخدمين",
        USERS_MANAGE: "إدارة المستخدمين والأدوار",
        SETTINGS_VIEW: "عرض الإعدادات",
        SETTINGS_MANAGE: "تعديل الإعدادات",
        BACKUP_MANAGE: "إدارة النسخ الاحتياطي",
        AUDIT_VIEW: "عرض سجل التدقيق",
    }

    @classmethod
    def all(cls) -> list[str]:
        return list(cls.CATALOG.keys())
