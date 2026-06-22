"""خدمة المبيعات (بيع مباشر: نقدي/آجل/جزئي).

الترحيل يربط: المخزون (صرف) + الخزينة (المقبوض) + رصيد العميل (المتبقّي) +
التدقيق، ضمن اليوم المفتوح فقط. الحذف يعكس كل ذلك ويُمنع على يوم مُقفل.

قواعد الدفع:
- نقدي: المقبوض = الإجمالي (لا مديونية).
- آجل: المقبوض = 0 (كامل الإجمالي مديونية على العميل).
- جزئي: المقبوض جزء، والباقي مديونية على العميل.
أي مبلغ متبقٍّ (آجل/جزئي) يستلزم اختيار عميل.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

from app.core.utils.formatters import business_date_key
from app.data.repositories.inventory_repository import InventoryRepository
from app.data.repositories.sales_repository import SalesRepository
from app.domain.entities import Sale, SaleItem
from app.services.audit_service import AuditService
from app.services.day_closing_service import DayClosingError, DayClosingService


class SalesServiceError(Exception):
    """خطأ في عمليات البيع مع رسالة عربية."""


class SalesService:
    def __init__(
        self,
        repo: SalesRepository,
        inventory_repo: InventoryRepository,
        day_closing: DayClosingService,
        audit: AuditService,
    ):
        self._repo = repo
        self._inventory = inventory_repo
        self._day_closing = day_closing
        self._audit = audit

    def create_sale(
        self,
        *,
        customer_id: int | None,
        lines: Sequence[dict],
        discount: float = 0.0,
        paid: float = 0.0,
        notes: str | None = None,
        actor_id: int | None = None,
    ) -> int:
        clean: list[dict] = []
        for ln in lines:
            qty = float(ln.get("quantity", 0))
            price = float(ln.get("unit_price", 0))
            if qty <= 0:
                raise SalesServiceError("كمية كل بند يجب أن تكون أكبر من صفر.")
            if price < 0:
                raise SalesServiceError("السعر لا يمكن أن يكون سالبًا.")
            clean.append(
                {
                    "item_id": ln.get("item_id"),
                    "description": ln.get("description", ""),
                    "quantity": qty,
                    "unit_price": price,
                }
            )
        if not clean:
            raise SalesServiceError("أضف بندًا واحدًا على الأقل للفاتورة.")

        gross = sum(c["quantity"] * c["unit_price"] for c in clean)
        if discount < 0:
            raise SalesServiceError("الخصم لا يمكن أن يكون سالبًا.")
        if discount > gross:
            raise SalesServiceError("الخصم أكبر من إجمالي الأصناف.")
        total = gross - discount
        if paid < 0:
            raise SalesServiceError("المقبوض لا يمكن أن يكون سالبًا.")
        if paid > total:
            raise SalesServiceError("المقبوض أكبر من إجمالي الفاتورة.")
        if paid < total and customer_id is None:
            raise SalesServiceError("البيع الآجل/الجزئي يتطلب اختيار عميل.")

        # توفّر المخزون قبل الترحيل.
        for c in clean:
            if c["item_id"] is not None:
                item = self._inventory.find_by_id(c["item_id"])
                if item is None:
                    raise SalesServiceError("صنف غير موجود في الفاتورة.")
                if c["quantity"] > item.quantity:
                    raise SalesServiceError(
                        f"الكمية المطلوبة من «{item.name}» ({c['quantity']}) "
                        f"أكبر من المتاح ({item.quantity})."
                    )

        try:
            day_id = self._day_closing.current_open_day_id()
        except DayClosingError as exc:
            raise SalesServiceError(str(exc)) from exc

        sale_id, total = self._repo.create_full(
            customer_id=customer_id,
            date=business_date_key(date.today()),
            day_id=day_id,
            user_id=actor_id,
            notes=notes,
            discount=discount,
            paid=paid,
            items=clean,
        )
        self._audit.log(
            "sale_create", user_id=actor_id, entity="sales", entity_id=sale_id,
            details=f"total={total:.2f} paid={paid:.2f}",
        )
        return sale_id

    def delete_sale(self, sale_id: int, actor_id: int | None = None) -> None:
        sale = self._repo.find_by_id(sale_id)
        if sale is None:
            raise SalesServiceError("الفاتورة غير موجودة.")
        if sale.day_id is not None and self._day_closing.is_day_closed(sale.day_id):
            raise SalesServiceError("لا يمكن حذف فاتورة ضمن يوم مُقفل.")
        self._repo.delete_full(sale_id, actor_id)
        self._audit.log(
            "sale_delete", user_id=actor_id, entity="sales", entity_id=sale_id
        )

    # ── استعلامات ───────────────────────────────────────────────────────
    def list(self, search: str = "") -> list[Sale]:
        return self._repo.list_recent(search)

    def get(self, sale_id: int) -> Sale | None:
        return self._repo.find_by_id(sale_id)

    def items(self, sale_id: int) -> list[SaleItem]:
        return self._repo.items(sale_id)
