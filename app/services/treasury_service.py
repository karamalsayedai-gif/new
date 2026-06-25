"""خدمة الخزينة الرئيسية.

تطبّق قواعد العمل المالية فوق المستودع:
- كل حركة تُوسم تلقائيًا بـ ``day_id`` لليوم المفتوح الحالي.
- يُمنع تسجيل أو حذف أي حركة في يوم مُقفل (عبر DayClosingService).
- كل حركة تُسجَّل في سجل التدقيق.

الخزينة هي مصدر النقد المتوقع في الإقفال اليومي (رصيد الافتتاح + صافي حركة اليوم).
"""
from __future__ import annotations

from app.core.utils.formatters import now_iso
from app.data.repositories.treasuries_repository import TreasuriesRepository
from app.data.repositories.treasury_repository import TreasuryRepository
from app.domain.enums import TreasuryCategory, TreasuryDirection
from app.services.audit_service import AuditService
from app.services.day_closing_service import DayClosingError, DayClosingService


class TreasuryError(Exception):
    """خطأ في عمليات الخزينة مع رسالة عربية."""


class TreasuryService:
    def __init__(
        self,
        repo: TreasuryRepository,
        day_closing: DayClosingService,
        audit: AuditService,
        accounts: TreasuriesRepository,
    ):
        self._repo = repo
        self._day_closing = day_closing
        self._audit = audit
        self._accounts = accounts

    # ── إدارة الخزائن ───────────────────────────────────────────────────
    def accounts(self):
        return self._accounts.list_all()

    def active_accounts(self):
        return self._accounts.list_active()

    def account_balances(self):
        return self._accounts.balances()

    def default_account_id(self) -> int | None:
        return self._accounts.default_id()

    def create_account(
        self, name: str, kind: str = "cash", user_id: int | None = None
    ) -> int:
        name = (name or "").strip()
        if not name:
            raise TreasuryError("اسم الخزنة مطلوب.")
        for acc in self._accounts.list_all():
            if acc["name"].strip() == name:
                raise TreasuryError("يوجد خزنة بنفس الاسم.")
        tid = self._accounts.create(name=name, kind=kind, created_at=now_iso())
        self._audit.log("treasury_account_create", user_id=user_id,
                        entity="treasuries", entity_id=tid)
        return tid

    def rename_account(
        self, treasury_id: int, name: str, kind: str = "cash",
        user_id: int | None = None,
    ) -> None:
        name = (name or "").strip()
        if not name:
            raise TreasuryError("اسم الخزنة مطلوب.")
        self._accounts.update(treasury_id, name=name, kind=kind)
        self._audit.log("treasury_account_update", user_id=user_id,
                        entity="treasuries", entity_id=treasury_id)

    def set_account_active(
        self, treasury_id: int, active: bool, user_id: int | None = None
    ) -> None:
        acc = self._accounts.find_by_id(treasury_id)
        if acc is None:
            raise TreasuryError("الخزنة غير موجودة.")
        if acc["is_default"] and not active:
            raise TreasuryError("لا يمكن تعطيل الخزنة الافتراضية.")
        self._accounts.set_active(treasury_id, active)

    def delete_account(self, treasury_id: int, user_id: int | None = None) -> None:
        acc = self._accounts.find_by_id(treasury_id)
        if acc is None:
            raise TreasuryError("الخزنة غير موجودة.")
        if acc["is_default"]:
            raise TreasuryError("لا يمكن حذف الخزنة الافتراضية.")
        if self._accounts.has_movements(treasury_id):
            raise TreasuryError("لا يمكن حذف خزنة بها حركات مالية. عطّلها بدلًا من ذلك.")
        self._accounts.delete(treasury_id)
        self._audit.log("treasury_account_delete", user_id=user_id,
                        entity="treasuries", entity_id=treasury_id)

    # ── التسجيل ─────────────────────────────────────────────────────────
    def add_entry(
        self,
        *,
        direction: str,
        category: str,
        amount: float,
        user_id: int | None,
        notes: str | None = None,
        treasury_id: int | None = None,
        ref_table: str | None = None,
        ref_id: int | None = None,
    ) -> int:
        if amount <= 0:
            raise TreasuryError("المبلغ يجب أن يكون أكبر من صفر.")
        if direction not in (TreasuryDirection.IN.value, TreasuryDirection.OUT.value):
            raise TreasuryError("اتجاه الحركة غير صحيح.")

        try:
            day_id = self._day_closing.current_open_day_id()
        except DayClosingError as exc:
            # تحويل الخطأ لرسالة خزينة واضحة.
            raise TreasuryError(str(exc)) from exc

        entry_id = self._repo.add(
            direction=direction,
            category=category,
            amount=amount,
            date=now_iso(),
            day_id=day_id,
            user_id=user_id,
            treasury_id=treasury_id,
            ref_table=ref_table,
            ref_id=ref_id,
            notes=notes,
        )
        self._audit.log(
            "treasury_add",
            user_id=user_id,
            entity="treasury",
            entity_id=entry_id,
            details=f"{direction}/{category} amount={amount:.2f}",
        )
        return entry_id

    def record_income(
        self, amount: float, notes: str | None, user_id: int | None,
        treasury_id: int | None = None,
    ) -> int:
        return self.add_entry(
            direction=TreasuryDirection.IN.value,
            category=TreasuryCategory.INCOME.value,
            amount=amount,
            user_id=user_id,
            notes=notes,
            treasury_id=treasury_id,
        )

    def record_expense(
        self, amount: float, notes: str | None, user_id: int | None,
        treasury_id: int | None = None,
    ) -> int:
        return self.add_entry(
            direction=TreasuryDirection.OUT.value,
            category=TreasuryCategory.EXPENSE.value,
            amount=amount,
            user_id=user_id,
            notes=notes,
            treasury_id=treasury_id,
        )

    def record_manual(
        self, direction: str, amount: float, notes: str | None, user_id: int | None,
        treasury_id: int | None = None,
    ) -> int:
        return self.add_entry(
            direction=direction,
            category=TreasuryCategory.MANUAL.value,
            amount=amount,
            user_id=user_id,
            notes=notes,
            treasury_id=treasury_id,
        )

    # ── الحذف (مع احترام قفل اليوم) ─────────────────────────────────────
    def delete_entry(self, entry_id: int, user_id: int | None) -> None:
        row = self._repo.find_by_id(entry_id)
        if row is None:
            raise TreasuryError("الحركة غير موجودة.")
        day_id = row["day_id"]
        if day_id is not None and self._day_closing.is_day_closed(day_id):
            raise TreasuryError("لا يمكن حذف حركة ضمن يوم مُقفل.")
        self._repo.delete(entry_id)
        self._audit.log(
            "treasury_delete", user_id=user_id, entity="treasury", entity_id=entry_id
        )

    # ── استعلامات ───────────────────────────────────────────────────────
    def current_balance(self, treasury_id: int | None = None) -> float:
        return self._repo.current_balance(treasury_id)

    def day_summary(self, day_id: int, treasury_id: int | None = None) -> dict[str, float]:
        total_in, total_out = self._repo.day_totals(day_id, treasury_id)
        return {"in": total_in, "out": total_out, "net": total_in - total_out}

    def list_for_day(self, day_id: int, treasury_id: int | None = None):
        return self._repo.list_for_day(day_id, treasury_id)

    def list_recent(self, limit: int = 200):
        return self._repo.list_recent(limit)
