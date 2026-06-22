"""خدمة التقسيط.

- إنشاء بيع تقسيط: يولّد جدول أقساط ويربط المخزون/الخزينة/رصيد العميل.
- تحصيل قسط: يوزّع المبلغ على الأقساط الأقدم، يضيف قبضًا للخزينة، ويخفّض مديونية
  العميل، ضمن اليوم المفتوح فقط.

العميل إجباري في بيع التقسيط. الفائدة (قيمة) تُوزَّع بالتساوي على الأشهر.
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Sequence

from app.core.constants.setting_keys import SettingKeys
from app.core.utils.formatters import business_date_key
from app.data.repositories.installments_repository import InstallmentsRepository
from app.data.repositories.inventory_repository import InventoryRepository
from app.domain.entities import Installment, InstallmentPlan
from app.services.audit_service import AuditService
from app.services.day_closing_service import DayClosingError, DayClosingService
from app.services.settings_service import SettingsService


class InstallmentsServiceError(Exception):
    """خطأ في عمليات التقسيط مع رسالة عربية."""


def _add_months(iso: str, n: int) -> str:
    d = date.fromisoformat(iso)
    total = d.month - 1 + n
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


class InstallmentsService:
    def __init__(
        self,
        repo: InstallmentsRepository,
        inventory_repo: InventoryRepository,
        day_closing: DayClosingService,
        audit: AuditService,
        settings: SettingsService,
    ):
        self._repo = repo
        self._inventory = inventory_repo
        self._day_closing = day_closing
        self._audit = audit
        self._settings = settings

    # ── إنشاء بيع تقسيط ─────────────────────────────────────────────────
    def create_plan(
        self,
        *,
        customer_id: int | None,
        lines: Sequence[dict],
        down_payment: float,
        months: int,
        interest: float,
        first_due_date: str,
        notes: str | None = None,
        actor_id: int | None = None,
    ) -> tuple[int, int]:
        if not customer_id:
            raise InstallmentsServiceError("بيع التقسيط يتطلب اختيار عميل.")
        if months < 1:
            raise InstallmentsServiceError("عدد الأقساط يجب أن يكون 1 على الأقل.")
        if interest < 0:
            raise InstallmentsServiceError("الفائدة لا يمكن أن تكون سالبة.")
        try:
            date.fromisoformat(first_due_date)
        except (ValueError, TypeError):
            raise InstallmentsServiceError("تاريخ أول قسط غير صحيح.")

        clean: list[dict] = []
        for ln in lines:
            qty = float(ln.get("quantity", 0))
            price = float(ln.get("unit_price", 0))
            if qty <= 0:
                raise InstallmentsServiceError("كمية كل بند يجب أن تكون أكبر من صفر.")
            if price < 0:
                raise InstallmentsServiceError("السعر لا يمكن أن يكون سالبًا.")
            clean.append(
                {
                    "item_id": ln.get("item_id"),
                    "description": ln.get("description", ""),
                    "quantity": qty,
                    "unit_price": price,
                }
            )
        if not clean:
            raise InstallmentsServiceError("أضف بندًا واحدًا على الأقل.")

        goods_total = sum(c["quantity"] * c["unit_price"] for c in clean)
        if down_payment < 0 or down_payment > goods_total:
            raise InstallmentsServiceError("المقدّم غير صحيح.")
        financed = goods_total - down_payment
        schedule_total = financed + interest
        sale_total = goods_total + interest

        # توفّر المخزون.
        for c in clean:
            if c["item_id"] is not None:
                item = self._inventory.find_by_id(c["item_id"])
                if item is None:
                    raise InstallmentsServiceError("صنف غير موجود.")
                if c["quantity"] > item.quantity:
                    raise InstallmentsServiceError(
                        f"الكمية المطلوبة من «{item.name}» أكبر من المتاح "
                        f"({item.quantity})."
                    )

        schedule = self._build_schedule(
            financed, interest, schedule_total, months, first_due_date
        )

        try:
            day_id = self._day_closing.current_open_day_id()
        except DayClosingError as exc:
            raise InstallmentsServiceError(str(exc)) from exc

        sale_id, plan_id = self._repo.create_installment_sale(
            customer_id=customer_id,
            date=business_date_key(date.today()),
            day_id=day_id,
            user_id=actor_id,
            notes=notes,
            sale_total=sale_total,
            down_payment=down_payment,
            schedule_total=schedule_total,
            months=months,
            interest=interest,
            items=clean,
            installments=schedule,
            invoice_prefix=self._settings.get(SettingKeys.SALES_NO_PREFIX, "ف-"),
        )
        self._audit.log(
            "installment_create", user_id=actor_id, entity="installment_plans",
            entity_id=plan_id,
            details=f"sale={sale_id} total={schedule_total:.2f} months={months}",
        )
        return sale_id, plan_id

    @staticmethod
    def _build_schedule(
        financed: float, interest: float, schedule_total: float, months: int,
        first_due: str,
    ) -> list[dict]:
        amount_each = round(schedule_total / months, 2)
        principal_each = round(financed / months, 2)
        interest_each = round(interest / months, 2)
        rows: list[dict] = []
        for i in range(1, months + 1):
            if i == months:
                # القسط الأخير يمتصّ فروق التقريب.
                amount = round(schedule_total - amount_each * (months - 1), 2)
                principal = round(financed - principal_each * (months - 1), 2)
                interest_i = round(interest - interest_each * (months - 1), 2)
            else:
                amount, principal, interest_i = amount_each, principal_each, interest_each
            rows.append(
                {
                    "number": i,
                    "due_date": _add_months(first_due, i - 1),
                    "amount": amount,
                    "principal": principal,
                    "interest": interest_i,
                }
            )
        return rows

    # ── التحصيل ─────────────────────────────────────────────────────────
    def collect(
        self, plan_id: int, amount: float, actor_id: int | None = None
    ) -> float:
        if amount <= 0:
            raise InstallmentsServiceError("مبلغ التحصيل يجب أن يكون أكبر من صفر.")
        plan = self._repo.find_plan(plan_id)
        if plan is None:
            raise InstallmentsServiceError("الخطة غير موجودة.")
        remaining = plan.total_amount - self._repo.plan_paid(plan_id)
        if remaining <= 0.0001:
            raise InstallmentsServiceError("الخطة مسدّدة بالكامل.")
        amount = min(amount, remaining)

        try:
            day_id = self._day_closing.current_open_day_id()
        except DayClosingError as exc:
            raise InstallmentsServiceError(str(exc)) from exc

        collected = self._repo.collect(
            plan_id=plan_id, amount=amount, day_id=day_id, user_id=actor_id
        )
        self._audit.log(
            "installment_collect", user_id=actor_id, entity="installment_plans",
            entity_id=plan_id, details=f"collected={collected:.2f}",
        )
        return collected

    # ── استعلامات ───────────────────────────────────────────────────────
    def list_plans(self, search: str = "") -> list[InstallmentPlan]:
        return self._repo.list_plans(search)

    def get_plan(self, plan_id: int) -> InstallmentPlan | None:
        return self._repo.find_plan(plan_id)

    def installments(self, plan_id: int) -> list[Installment]:
        return self._repo.installments_for_plan(plan_id)

    def collections(self, plan_id: int):
        return self._repo.collections_for_plan(plan_id)

    def plan_paid(self, plan_id: int) -> float:
        return self._repo.plan_paid(plan_id)

    def overdue_by_customer(self):
        today = business_date_key(date.today())
        return self._repo.overdue_by_customer(today)

    def due_today(self):
        today = business_date_key(date.today())
        return self._repo.due_on(today)

    @staticmethod
    def today_key() -> str:
        return business_date_key(date.today())
