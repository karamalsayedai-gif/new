"""خدمة المشتريات.

ترحيل فاتورة شراء يربط: المخزون (دخول) + الخزينة (صرف المدفوع) + رصيد المورّد
(المتبقّي) + سجل التدقيق، ضمن اليوم المفتوح فقط. الحذف يعكس كل ذلك ويُمنع على
يوم مُقفل.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

from app.core.constants.setting_keys import SettingKeys
from app.core.utils.formatters import business_date_key
from app.data.repositories.purchases_repository import PurchasesRepository
from app.domain.entities import Purchase, PurchaseItem
from app.services.audit_service import AuditService
from app.services.day_closing_service import DayClosingError, DayClosingService
from app.services.settings_service import SettingsService


class PurchasesServiceError(Exception):
    """خطأ في عمليات المشتريات مع رسالة عربية."""


class PurchasesService:
    def __init__(
        self,
        repo: PurchasesRepository,
        day_closing: DayClosingService,
        audit: AuditService,
        settings: SettingsService,
    ):
        self._repo = repo
        self._day_closing = day_closing
        self._audit = audit
        self._settings = settings

    # ── الترحيل ─────────────────────────────────────────────────────────
    def create_purchase(
        self,
        *,
        supplier_id: int,
        lines: Sequence[dict],
        paid: float,
        notes: str | None = None,
        actor_id: int | None = None,
        treasury_id: int | None = None,
    ) -> int:
        if not supplier_id:
            raise PurchasesServiceError("يجب اختيار المورّد.")
        clean: list[dict] = []
        for ln in lines:
            qty = float(ln.get("quantity", 0))
            cost = float(ln.get("unit_cost", 0))
            if qty <= 0:
                raise PurchasesServiceError("كمية كل بند يجب أن تكون أكبر من صفر.")
            if cost < 0:
                raise PurchasesServiceError("التكلفة لا يمكن أن تكون سالبة.")
            clean.append(
                {
                    "item_id": ln.get("item_id"),
                    "description": ln.get("description", ""),
                    "quantity": qty,
                    "unit_cost": cost,
                }
            )
        if not clean:
            raise PurchasesServiceError("أضف بندًا واحدًا على الأقل للفاتورة.")

        total = sum(c["quantity"] * c["unit_cost"] for c in clean)
        if paid < 0:
            raise PurchasesServiceError("المبلغ المدفوع لا يمكن أن يكون سالبًا.")
        if paid > total:
            raise PurchasesServiceError("المدفوع أكبر من إجمالي الفاتورة.")

        try:
            day_id = self._day_closing.current_open_day_id()
        except DayClosingError as exc:
            raise PurchasesServiceError(str(exc)) from exc

        purchase_id, total, invoice_no = self._repo.create_full(
            supplier_id=supplier_id,
            date=business_date_key(date.today()),
            day_id=day_id,
            user_id=actor_id,
            notes=notes,
            paid=paid,
            items=clean,
            invoice_prefix=self._settings.get(SettingKeys.PURCHASE_NO_PREFIX, "ش-"),
            treasury_id=treasury_id,
        )
        self._audit.log(
            "purchase_create", user_id=actor_id, entity="purchases",
            entity_id=purchase_id,
            details=f"{invoice_no} total={total:.2f} paid={paid:.2f}",
        )
        return purchase_id

    def delete_purchase(self, purchase_id: int, actor_id: int | None = None) -> None:
        purchase = self._repo.find_by_id(purchase_id)
        if purchase is None:
            raise PurchasesServiceError("الفاتورة غير موجودة.")
        if purchase.day_id is not None and self._day_closing.is_day_closed(
            purchase.day_id
        ):
            raise PurchasesServiceError(
                "لا يمكن حذف فاتورة ضمن يوم مُقفل."
            )
        self._repo.delete_full(purchase_id, actor_id)
        self._audit.log(
            "purchase_delete", user_id=actor_id, entity="purchases",
            entity_id=purchase_id,
        )

    # ── استعلامات ───────────────────────────────────────────────────────
    def list(self, search: str = "") -> list[Purchase]:
        return self._repo.list_recent(search)

    def get(self, purchase_id: int) -> Purchase | None:
        return self._repo.find_by_id(purchase_id)

    def items(self, purchase_id: int) -> list[PurchaseItem]:
        return self._repo.items(purchase_id)
