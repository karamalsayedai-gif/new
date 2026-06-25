"""تعبئة البيانات الأولية عند إنشاء قاعدة البيانات لأول مرة.

كتالوج الصلاحيات، الأدوار النظامية، ربط الصلاحيات، والإعدادات الافتراضية.

ملاحظة: لا يُنشأ مستخدم Admin هنا — يُنشأ في تدفّق "الإعداد لأول مرة" ليختار
صاحب المعرض بياناته.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.constants.permissions import Permissions
from app.core.constants.setting_keys import SettingKeys
from app.core.utils.formatters import now_iso

if TYPE_CHECKING:
    from app.data.database import Database

# أسماء الأدوار النظامية (تُستخدم أيضًا في الخدمات للعثور على دور المدير).
ROLE_ADMIN = "مدير النظام"
ROLE_CASHIER = "كاشير"
ROLE_ACCOUNTANT = "محاسب"

_CASHIER_PERMS = [
    Permissions.INVENTORY_VIEW,
    Permissions.CUSTOMERS_VIEW,
    Permissions.CUSTOMERS_MANAGE,
    Permissions.SALES_CASH_VIEW,
    Permissions.SALES_CASH_CREATE,
    Permissions.SALES_INSTALLMENT_VIEW,
    Permissions.SALES_INSTALLMENT_CREATE,
    Permissions.INSTALLMENTS_COLLECT,
    Permissions.TREASURY_VIEW,
]

_ACCOUNTANT_PERMS = [
    Permissions.INVENTORY_VIEW,
    Permissions.SUPPLIERS_VIEW,
    Permissions.PURCHASES_VIEW,
    Permissions.PURCHASES_MANAGE,
    Permissions.CUSTOMERS_VIEW,
    Permissions.SALES_CASH_VIEW,
    Permissions.SALES_INSTALLMENT_VIEW,
    Permissions.TREASURY_VIEW,
    Permissions.TREASURY_MANAGE,
    Permissions.EXPENSES_VIEW,
    Permissions.EXPENSES_MANAGE,
    Permissions.REPORTS_VIEW,
    Permissions.DAY_CLOSE,
    Permissions.AUDIT_VIEW,
]


def seed_initial_data(db: "Database") -> None:
    now = now_iso()
    with db.transaction() as conn:
        # 1) كتالوج الصلاحيات
        conn.executemany(
            "INSERT INTO permissions(code, description) VALUES (?, ?)",
            list(Permissions.CATALOG.items()),
        )

        # 2) الأدوار النظامية
        role_ids: dict[str, int] = {}
        for name in (ROLE_ADMIN, ROLE_CASHIER, ROLE_ACCOUNTANT):
            cur = conn.execute(
                "INSERT INTO roles(name, is_system, created_at) VALUES (?, 1, ?)",
                (name, now),
            )
            role_ids[name] = int(cur.lastrowid)

        # 3) ربط الصلاحيات بالأدوار
        def grant(role_id: int, codes: list[str]) -> None:
            conn.executemany(
                "INSERT INTO role_permissions(role_id, permission_code) VALUES (?, ?)",
                [(role_id, code) for code in codes],
            )

        grant(role_ids[ROLE_ADMIN], Permissions.all())
        grant(role_ids[ROLE_CASHIER], _CASHIER_PERMS)
        grant(role_ids[ROLE_ACCOUNTANT], _ACCOUNTANT_PERMS)

        # 4) الإعدادات الافتراضية
        conn.executemany(
            "INSERT INTO settings(key, value, type) VALUES (?, ?, ?)",
            [
                (key, default, type_)
                for key, (default, type_) in SettingKeys.DEFAULTS.items()
            ],
        )

        # 5) الخزائن الافتراضية (الرئيسية + خزنة مبيعات اليوم).
        conn.executemany(
            "INSERT INTO treasuries(name, kind, is_default, is_active, created_at) "
            "VALUES (?, ?, ?, 1, ?)",
            [
                ("الخزنة الرئيسية", "cash", 1, now),
                ("خزنة مبيعات اليوم", "cash", 0, now),
            ],
        )
