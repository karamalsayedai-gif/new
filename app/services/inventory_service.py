"""خدمة المخزون: قواعد العمل فوق المستودع.

تشمل تعريف الأصناف، تعديل المخزون مع تسجيل الحركة، تنبيهات النقص، والتحقق.
"""
from __future__ import annotations

from app.core.utils.formatters import now_iso
from app.data.repositories.inventory_repository import InventoryRepository
from app.domain.entities import InventoryItem
from app.domain.enums import ItemStatus, StockDirection
from app.services.audit_service import AuditService


class InventoryServiceError(Exception):
    """خطأ في إدارة المخزون مع رسالة عربية."""


class InventoryService:
    def __init__(self, repo: InventoryRepository, audit: AuditService):
        self._repo = repo
        self._audit = audit

    # ── استعلامات ───────────────────────────────────────────────────────
    def list(
        self,
        *,
        search: str = "",
        category: str = "",
        status: str = "",
        only_low: bool = False,
    ) -> list[InventoryItem]:
        return self._repo.list_items(
            search=search, category=category, status=status, only_low=only_low
        )

    def get(self, item_id: int) -> InventoryItem | None:
        return self._repo.find_by_id(item_id)

    def categories(self) -> list[str]:
        return self._repo.categories()

    def low_stock(self, default_threshold: int = 0) -> list[InventoryItem]:
        return self._repo.list_low_stock(default_threshold)

    def count(self) -> int:
        return self._repo.count()

    def movements(self, item_id: int, limit: int = 100):
        return self._repo.list_movements(item_id, limit)

    # ── تعريف الأصناف ───────────────────────────────────────────────────
    def create(
        self,
        *,
        name: str,
        category: str = "",
        unit: str = "قطعة",
        quantity: float = 0.0,
        min_stock: float = 0.0,
        unit_cost: float = 0.0,
        sale_price: float = 0.0,
        status: str = ItemStatus.ACTIVE.value,
        actor_id: int | None = None,
    ) -> int:
        self._validate(name, quantity, min_stock, unit_cost, sale_price)
        # يُنشأ الصنف برصيد صفر، ثم يُطبَّق الرصيد الافتتاحي عبر حركة دخول واحدة
        # لتبقى الكمية مصدرها الوحيد هو سجل الحركة (تفادي ازدواج العد).
        item_id = self._repo.create(
            name=name.strip(),
            category=category.strip(),
            unit=unit.strip() or "قطعة",
            quantity=0.0,
            min_stock=min_stock,
            unit_cost=unit_cost,
            sale_price=sale_price,
            status=status,
            created_at=now_iso(),
        )
        # رصيد افتتاحي يُسجَّل كحركة دخول.
        if quantity > 0:
            self._repo.record_movement(
                item_id=item_id, direction=StockDirection.IN.value,
                quantity=quantity, reason="رصيد افتتاحي", user_id=actor_id,
                created_at=now_iso(),
            )
        self._audit.log(
            "item_create", user_id=actor_id, entity="inventory_items",
            entity_id=item_id,
        )
        return item_id

    def update(
        self,
        item_id: int,
        *,
        name: str,
        category: str = "",
        unit: str = "قطعة",
        min_stock: float = 0.0,
        unit_cost: float = 0.0,
        sale_price: float = 0.0,
        status: str = ItemStatus.ACTIVE.value,
        actor_id: int | None = None,
    ) -> None:
        self._validate(name, 0.0, min_stock, unit_cost, sale_price)
        self._repo.update(
            item_id,
            name=name.strip(),
            category=category.strip(),
            unit=unit.strip() or "قطعة",
            min_stock=min_stock,
            unit_cost=unit_cost,
            sale_price=sale_price,
            status=status,
        )
        self._audit.log(
            "item_update", user_id=actor_id, entity="inventory_items",
            entity_id=item_id,
        )

    def delete(self, item_id: int, actor_id: int | None = None) -> None:
        if self._repo.has_sales(item_id):
            raise InventoryServiceError(
                "لا يمكن حذف صنف مرتبط بعمليات بيع."
            )
        self._repo.delete(item_id)
        self._audit.log(
            "item_delete", user_id=actor_id, entity="inventory_items",
            entity_id=item_id,
        )

    # ── حركة المخزون ────────────────────────────────────────────────────
    def adjust_stock(
        self,
        item_id: int,
        direction: str,
        quantity: float,
        reason: str | None,
        actor_id: int | None = None,
        ref_table: str | None = None,
        ref_id: int | None = None,
    ) -> int:
        if quantity <= 0:
            raise InventoryServiceError("الكمية يجب أن تكون أكبر من صفر.")
        item = self._repo.find_by_id(item_id)
        if item is None:
            raise InventoryServiceError("الصنف غير موجود.")
        if direction == StockDirection.OUT.value and quantity > item.quantity:
            raise InventoryServiceError(
                f"الكمية المطلوبة ({quantity}) أكبر من المتاح ({item.quantity})."
            )
        movement_id = self._repo.record_movement(
            item_id=item_id, direction=direction, quantity=quantity,
            reason=reason, user_id=actor_id, created_at=now_iso(),
            ref_table=ref_table, ref_id=ref_id,
        )
        self._audit.log(
            "stock_adjust", user_id=actor_id, entity="inventory_items",
            entity_id=item_id, details=f"{direction} qty={quantity}",
        )
        return movement_id

    # ── تحقق ────────────────────────────────────────────────────────────
    @staticmethod
    def _validate(
        name: str, quantity: float, min_stock: float, unit_cost: float,
        sale_price: float,
    ) -> None:
        if not name.strip():
            raise InventoryServiceError("اسم الصنف مطلوب.")
        if quantity < 0 or min_stock < 0 or unit_cost < 0 or sale_price < 0:
            raise InventoryServiceError("القيم الرقمية لا يمكن أن تكون سالبة.")
