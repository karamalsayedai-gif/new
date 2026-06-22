"""خدمة الموردين: التحقق وقواعد العمل فوق المستودع."""
from __future__ import annotations

from app.core.utils.formatters import now_iso
from app.data.repositories.suppliers_repository import SuppliersRepository
from app.domain.entities import Supplier
from app.services.audit_service import AuditService


class SuppliersServiceError(Exception):
    """خطأ في إدارة الموردين مع رسالة عربية."""


class SuppliersService:
    def __init__(self, repo: SuppliersRepository, audit: AuditService):
        self._repo = repo
        self._audit = audit

    def list(self, search: str = "") -> list[Supplier]:
        return self._repo.list_all(search)

    def get(self, supplier_id: int) -> Supplier | None:
        return self._repo.find_by_id(supplier_id)

    def count(self) -> int:
        return self._repo.count()

    def create(
        self,
        *,
        name: str,
        phone: str = "",
        address: str = "",
        actor_id: int | None = None,
    ) -> int:
        name = name.strip()
        if not name:
            raise SuppliersServiceError("اسم المورّد مطلوب.")
        supplier_id = self._repo.create(
            name=name, phone=phone.strip(), address=address.strip(),
            created_at=now_iso(),
        )
        self._audit.log(
            "supplier_create", user_id=actor_id, entity="suppliers",
            entity_id=supplier_id,
        )
        return supplier_id

    def update(
        self,
        supplier_id: int,
        *,
        name: str,
        phone: str = "",
        address: str = "",
        actor_id: int | None = None,
    ) -> None:
        name = name.strip()
        if not name:
            raise SuppliersServiceError("اسم المورّد مطلوب.")
        self._repo.update(
            supplier_id, name=name, phone=phone.strip(), address=address.strip()
        )
        self._audit.log(
            "supplier_update", user_id=actor_id, entity="suppliers",
            entity_id=supplier_id,
        )

    # ── كشف الحساب ──────────────────────────────────────────────────────
    def purchases(self, supplier_id: int):
        return self._repo.purchases(supplier_id)

    def payments(self, supplier_id: int):
        return self._repo.payments(supplier_id)

    def delete(self, supplier_id: int, actor_id: int | None = None) -> None:
        if self._repo.has_purchases(supplier_id):
            raise SuppliersServiceError(
                "لا يمكن حذف مورّد له مشتريات مسجّلة."
            )
        self._repo.delete(supplier_id)
        self._audit.log(
            "supplier_delete", user_id=actor_id, entity="suppliers",
            entity_id=supplier_id,
        )
