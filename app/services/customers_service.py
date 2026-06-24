"""خدمة العملاء: التحقق وقواعد العمل فوق المستودع."""
from __future__ import annotations

from app.core.utils.formatters import now_iso
from app.data.repositories.customers_repository import CustomersRepository
from app.domain.entities import Customer
from app.services.audit_service import AuditService


class CustomersServiceError(Exception):
    """خطأ في إدارة العملاء مع رسالة عربية."""


class CustomersService:
    def __init__(self, repo: CustomersRepository, audit: AuditService):
        self._repo = repo
        self._audit = audit

    def list(self, search: str = "") -> list[Customer]:
        return self._repo.list_all(search)

    def get(self, customer_id: int) -> Customer | None:
        return self._repo.find_by_id(customer_id)

    def get_or_create_by_name(self, name: str, actor_id: int | None = None) -> int:
        """يعيد معرّف عميل بالاسم؛ ينشئه تلقائيًا إن لم يكن موجودًا.

        يتيح كتابة اسم العميل مباشرة في فاتورة البيع دون تسجيله مسبقًا.
        """
        name = name.strip()
        if not name:
            raise CustomersServiceError("اسم العميل مطلوب.")
        for cust in self._repo.list_all(name):
            if cust.name.strip() == name:
                return cust.id
        return self.create(name=name, actor_id=actor_id)

    def count(self) -> int:
        return self._repo.count()

    def create(
        self,
        *,
        name: str,
        phone: str = "",
        national_id: str = "",
        address: str = "",
        credit_limit: float = 0.0,
        actor_id: int | None = None,
    ) -> int:
        name = name.strip()
        if not name:
            raise CustomersServiceError("اسم العميل مطلوب.")
        if credit_limit < 0:
            raise CustomersServiceError("الحد الائتماني لا يمكن أن يكون سالبًا.")
        customer_id = self._repo.create(
            name=name,
            phone=phone.strip(),
            national_id=national_id.strip(),
            address=address.strip(),
            credit_limit=credit_limit,
            created_at=now_iso(),
        )
        self._audit.log(
            "customer_create", user_id=actor_id, entity="customers",
            entity_id=customer_id,
        )
        return customer_id

    def update(
        self,
        customer_id: int,
        *,
        name: str,
        phone: str = "",
        national_id: str = "",
        address: str = "",
        credit_limit: float = 0.0,
        actor_id: int | None = None,
    ) -> None:
        name = name.strip()
        if not name:
            raise CustomersServiceError("اسم العميل مطلوب.")
        if credit_limit < 0:
            raise CustomersServiceError("الحد الائتماني لا يمكن أن يكون سالبًا.")
        self._repo.update(
            customer_id,
            name=name,
            phone=phone.strip(),
            national_id=national_id.strip(),
            address=address.strip(),
            credit_limit=credit_limit,
        )
        self._audit.log(
            "customer_update", user_id=actor_id, entity="customers",
            entity_id=customer_id,
        )

    # ── كشف الحساب ──────────────────────────────────────────────────────
    def sales(self, customer_id: int):
        return self._repo.sales(customer_id)

    def installments(self, customer_id: int):
        return self._repo.installments(customer_id)

    def payments(self, customer_id: int):
        return self._repo.payments(customer_id)

    def delete(self, customer_id: int, actor_id: int | None = None) -> None:
        if self._repo.has_sales(customer_id):
            raise CustomersServiceError(
                "لا يمكن حذف عميل له عمليات بيع مسجّلة."
            )
        self._repo.delete(customer_id)
        self._audit.log(
            "customer_delete", user_id=actor_id, entity="customers",
            entity_id=customer_id,
        )
