"""سجل عناصر التنقل (الوحدات) — مصدر واحد للحقيقة لقائمة الشريط الجانبي.

كل عنصر يحمل: المفتاح، التسمية العربية، الصلاحية المطلوبة (أو None للعام)،
ودالة إنشاء الواجهة (lazy). إضافة وحدة جديدة في المرحلة 3 = سطر واحد هنا.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from PyQt6.QtWidgets import QWidget

from app.core.constants.permissions import Permissions
from app.ui.customers.customers_view import CustomersView
from app.ui.audit.audit_view import AuditView
from app.ui.backup.backup_view import BackupView
from app.ui.day_closing.day_closing_view import DayClosingView
from app.ui.installments.installments_view import InstallmentsView
from app.ui.inventory.inventory_view import InventoryView
from app.ui.modules.dashboard_view import DashboardView
from app.ui.modules.placeholder_view import PlaceholderView
from app.ui.purchases.purchases_view import PurchasesView
from app.ui.reports.reports_view import ReportsView
from app.ui.sales.sales_view import SalesView
from app.ui.settings.settings_view import SettingsView
from app.ui.suppliers.suppliers_view import SuppliersView
from app.ui.treasury.treasury_view import TreasuryView
from app.ui.users.users_view import UsersView

if TYPE_CHECKING:
    from app.core.container import Container


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    permission: str | None
    factory: Callable[["Container"], QWidget]


def _placeholder(title: str) -> Callable[["Container"], QWidget]:
    return lambda _c: PlaceholderView(title)


def build_nav_items() -> list[NavItem]:
    return [
        NavItem("dashboard", "لوحة التحكم", None, lambda c: DashboardView(c)),
        NavItem(
            "inventory", "المخزون", Permissions.INVENTORY_VIEW,
            lambda c: InventoryView(c),
        ),
        NavItem(
            "purchases", "المشتريات", Permissions.PURCHASES_VIEW,
            lambda c: PurchasesView(c),
        ),
        NavItem(
            "suppliers", "الموردون", Permissions.SUPPLIERS_VIEW,
            lambda c: SuppliersView(c),
        ),
        NavItem(
            "customers", "العملاء", Permissions.CUSTOMERS_VIEW,
            lambda c: CustomersView(c),
        ),
        NavItem(
            "sales", "المبيعات", Permissions.SALES_CASH_VIEW,
            lambda c: SalesView(c),
        ),
        NavItem(
            "installments", "التقسيط", Permissions.SALES_INSTALLMENT_VIEW,
            lambda c: InstallmentsView(c),
        ),
        NavItem(
            "treasury", "الخزينة", Permissions.TREASURY_VIEW,
            lambda c: TreasuryView(c),
        ),
        NavItem(
            "expenses", "المصروفات والإيرادات", Permissions.EXPENSES_VIEW,
            _placeholder("المصروفات والإيرادات"),
        ),
        NavItem(
            "day_closing", "الإقفال اليومي", Permissions.DAY_CLOSE,
            lambda c: DayClosingView(c),
        ),
        NavItem(
            "reports", "التقارير", Permissions.REPORTS_VIEW,
            lambda c: ReportsView(c),
        ),
        NavItem(
            "users", "المستخدمون", Permissions.USERS_VIEW, lambda c: UsersView(c)
        ),
        NavItem(
            "audit", "سجل التدقيق", Permissions.AUDIT_VIEW,
            lambda c: AuditView(c),
        ),
        NavItem(
            "backup", "النسخ الاحتياطي", Permissions.BACKUP_MANAGE,
            lambda c: BackupView(c),
        ),
        NavItem(
            "settings", "الإعدادات", Permissions.SETTINGS_VIEW,
            lambda c: SettingsView(c),
        ),
    ]
