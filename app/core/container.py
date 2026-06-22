"""حاوية التبعيات: نقطة تجميع وإنشاء كل الكائنات المشتركة (DI بسيط).

تُنشأ مرة واحدة عند الإقلاع وتُمرَّر إلى الواجهات لتصل إلى الخدمات دون أن
تعرف الواجهة شيئًا عن طبقة البيانات.
"""
from __future__ import annotations

from app.config import AppConfig
from app.data.database import Database
from app.data.repositories.customers_repository import CustomersRepository
from app.data.repositories.day_closing_repository import DayClosingRepository
from app.data.repositories.installments_repository import InstallmentsRepository
from app.data.repositories.inventory_repository import InventoryRepository
from app.data.repositories.purchases_repository import PurchasesRepository
from app.data.repositories.reports_repository import ReportsRepository
from app.data.repositories.sales_repository import SalesRepository
from app.data.repositories.settings_repository import SettingsRepository
from app.data.repositories.suppliers_repository import SuppliersRepository
from app.data.repositories.treasury_repository import TreasuryRepository
from app.data.repositories.users_repository import UsersRepository
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.customers_service import CustomersService
from app.services.day_closing_service import DayClosingService
from app.services.installments_service import InstallmentsService
from app.services.inventory_service import InventoryService
from app.services.purchases_service import PurchasesService
from app.services.reports_service import ReportsService
from app.services.sales_service import SalesService
from app.services.settings_service import SettingsService
from app.services.suppliers_service import SuppliersService
from app.services.treasury_service import TreasuryService
from app.services.users_service import UsersService


class Container:
    def __init__(self) -> None:
        # طبقة البيانات
        self.db = Database(AppConfig.database_path())

        # المستودعات
        self.settings_repo = SettingsRepository(self.db)
        self.users_repo = UsersRepository(self.db)
        self.day_closing_repo = DayClosingRepository(self.db)
        self.treasury_repo = TreasuryRepository(self.db)
        self.customers_repo = CustomersRepository(self.db)
        self.suppliers_repo = SuppliersRepository(self.db)
        self.inventory_repo = InventoryRepository(self.db)
        self.purchases_repo = PurchasesRepository(self.db)
        self.sales_repo = SalesRepository(self.db)
        self.installments_repo = InstallmentsRepository(self.db)
        self.reports_repo = ReportsRepository(self.db)

        # الخدمات
        self.audit = AuditService(self.db)
        self.settings = SettingsService(self.settings_repo)
        self.auth = AuthService(self.users_repo, self.audit)
        self.users = UsersService(self.users_repo, self.audit)
        self.customers = CustomersService(self.customers_repo, self.audit)
        self.suppliers = SuppliersService(self.suppliers_repo, self.audit)
        self.inventory = InventoryService(self.inventory_repo, self.audit)
        self.day_closing = DayClosingService(self.day_closing_repo, self.audit)
        self.treasury = TreasuryService(
            self.treasury_repo, self.day_closing, self.audit
        )
        self.purchases = PurchasesService(
            self.purchases_repo, self.day_closing, self.audit
        )
        self.sales = SalesService(
            self.sales_repo, self.inventory_repo, self.day_closing, self.audit
        )
        self.installments = InstallmentsService(
            self.installments_repo, self.inventory_repo, self.day_closing, self.audit
        )
        self.reports = ReportsService(self.reports_repo, self.installments_repo)
        self.backup = BackupService(self.db, self.settings, self.audit)

        # محرك القوالب يُهيّأ بعد إنشاء QApplication.
        self.theme = None
        # مدير التنقّل بين الصفحات الكاملة (يُهيّأ في النافذة الرئيسية).
        self.navigator = None

    def initialize(self) -> None:
        """تهيئة قاعدة البيانات وتحميل الإعدادات."""
        self.db.initialize()
        self.settings.load()
