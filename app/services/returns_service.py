"""خدمة المرتجعات (بيع/شراء).

تتحقق من الكميات (ألّا تتجاوز المباع/المشترى ناقص ما أُرجع سابقًا)، تربط العملية
بالمخزون والخزينة وحساب العميل/المورّد، ضمن اليوم المفتوح، وتُدوّن في التدقيق.
"""
from __future__ import annotations

from datetime import date
from typing import Sequence

from app.core.utils.formatters import business_date_key
from app.data.repositories.purchases_repository import PurchasesRepository
from app.data.repositories.returns_repository import ReturnsRepository
from app.data.repositories.sales_repository import SalesRepository
from app.services.audit_service import AuditService
from app.services.day_closing_service import DayClosingError, DayClosingService


class ReturnsServiceError(Exception):
    """خطأ في عمليات المرتجعات مع رسالة عربية."""


class ReturnsService:
    def __init__(
        self,
        repo: ReturnsRepository,
        sales_repo: SalesRepository,
        purchases_repo: PurchasesRepository,
        day_closing: DayClosingService,
        audit: AuditService,
    ):
        self._repo = repo
        self._sales = sales_repo
        self._purchases = purchases_repo
        self._day_closing = day_closing
        self._audit = audit

    # ── مرتجع بيع ───────────────────────────────────────────────────────
    def create_sale_return(
        self, *, sale_id: int, lines: Sequence[dict], refund: float,
        notes: str | None = None, actor_id: int | None = None,
    ) -> int:
        sale = self._sales.find_by_id(sale_id)
        if sale is None:
            raise ReturnsServiceError("الفاتورة غير موجودة.")
        clean = self._validate_lines(
            lines, sold=self._sold_map(self._sales.items(sale_id)),
            already=self._repo.returned_qty("sale", sale_id),
        )
        total = sum(c["quantity"] * c["unit_price"] for c in clean)
        refund = self._check_refund(refund, total, sale.customer_id)
        day_id = self._open_day()
        return_id, total = self._repo.create_sale_return(
            sale_id=sale_id, date=business_date_key(date.today()), day_id=day_id,
            user_id=actor_id, notes=notes, refund=refund, items=clean,
        )
        self._audit.log(
            "sale_return", user_id=actor_id, entity="returns", entity_id=return_id,
            details=f"sale={sale_id} total={total:.2f} refund={refund:.2f}",
        )
        return return_id

    # ── مرتجع شراء ──────────────────────────────────────────────────────
    def create_purchase_return(
        self, *, purchase_id: int, lines: Sequence[dict], refund: float,
        notes: str | None = None, actor_id: int | None = None,
    ) -> int:
        purchase = self._purchases.find_by_id(purchase_id)
        if purchase is None:
            raise ReturnsServiceError("الفاتورة غير موجودة.")
        clean = self._validate_lines(
            lines, sold=self._cost_map(self._purchases.items(purchase_id)),
            already=self._repo.returned_qty("purchase", purchase_id),
        )
        total = sum(c["quantity"] * c["unit_price"] for c in clean)
        refund = self._check_refund(refund, total, purchase.supplier_id)
        day_id = self._open_day()
        return_id, total = self._repo.create_purchase_return(
            purchase_id=purchase_id, date=business_date_key(date.today()),
            day_id=day_id, user_id=actor_id, notes=notes, refund=refund, items=clean,
        )
        self._audit.log(
            "purchase_return", user_id=actor_id, entity="returns",
            entity_id=return_id,
            details=f"purchase={purchase_id} total={total:.2f} refund={refund:.2f}",
        )
        return return_id

    # ── مساعدات ─────────────────────────────────────────────────────────
    @staticmethod
    def _sold_map(items) -> dict[int, tuple[float, float]]:
        return {it.item_id: (it.quantity, it.unit_price) for it in items if it.item_id}

    @staticmethod
    def _cost_map(items) -> dict[int, tuple[float, float]]:
        return {it.item_id: (it.quantity, it.unit_cost) for it in items if it.item_id}

    def _validate_lines(self, lines, sold, already) -> list[dict]:
        clean: list[dict] = []
        for ln in lines:
            qty = float(ln.get("quantity", 0))
            if qty <= 0:
                continue
            item_id = ln.get("item_id")
            if item_id is not None and item_id in sold:
                max_qty = sold[item_id][0] - already.get(item_id, 0)
                if qty > max_qty + 1e-6:
                    raise ReturnsServiceError(
                        f"الكمية المُرتجعة ({qty:g}) أكبر من المتاح للإرجاع "
                        f"({max(max_qty, 0):g}) للصنف «{ln.get('description', '')}»."
                    )
            clean.append({
                "item_id": item_id, "description": ln.get("description", ""),
                "quantity": qty, "unit_price": float(ln.get("unit_price", 0)),
            })
        if not clean:
            raise ReturnsServiceError("حدّد كمية واحدة على الأقل للإرجاع.")
        return clean

    @staticmethod
    def _check_refund(refund: float, total: float, party_id: int | None) -> float:
        if refund < 0:
            raise ReturnsServiceError("المبلغ المُعاد لا يمكن أن يكون سالبًا.")
        if refund > total + 1e-6:
            raise ReturnsServiceError("المبلغ المُعاد أكبر من قيمة المرتجع.")
        if party_id is None and abs(refund - total) > 1e-6:
            raise ReturnsServiceError(
                "فاتورة نقدية بدون حساب: يجب ردّ كامل قيمة المرتجع نقدًا."
            )
        return refund

    def _open_day(self) -> int:
        try:
            return self._day_closing.current_open_day_id()
        except DayClosingError as exc:
            raise ReturnsServiceError(str(exc)) from exc

    def list_for_sale(self, sale_id: int):
        return self._repo.list_for_ref("sale", sale_id)

    def list_for_purchase(self, purchase_id: int):
        return self._repo.list_for_ref("purchase", purchase_id)
