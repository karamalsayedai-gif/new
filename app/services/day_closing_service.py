"""خدمة الإقفال اليومي.

القاعدة الأساسية: لكل يوم سجل في day_closings. عند الإقفال يُحسب النقد المتوقع
ويُقارن بالمعدول، ثم يُقفل اليوم فتُرفض أي عملية مالية جديدة على ذلك اليوم.
"""
from __future__ import annotations

from datetime import date

from app.core.utils.formatters import business_date_key, now_iso
from app.data.repositories.day_closing_repository import DayClosingRepository
from app.domain.entities import DayClosing
from app.domain.enums import DayStatus
from app.services.audit_service import AuditService


class DayClosingError(Exception):
    """خطأ في عمليات الإقفال اليومي مع رسالة عربية."""


class DayClosingService:
    def __init__(self, repo: DayClosingRepository, audit: AuditService):
        self._repo = repo
        self._audit = audit

    def get_or_open_today(self) -> DayClosing:
        """يعيد سجل اليوم الحالي، وينشئه (مفتوحًا) إن لم يوجد."""
        key = business_date_key(date.today())
        row = self._repo.find_by_date(key)
        if row is None:
            opening = self._repo.last_closed_counted()
            day_id = self._repo.open_day(key, opening, now_iso())
            row = self._repo.find_by_id(day_id)
        return DayClosing.from_row(row)

    def current_open_day_id(self) -> int:
        """معرّف اليوم الحالي لوسم العمليات؛ يرفض إن كان اليوم مُقفلًا."""
        day = self.get_or_open_today()
        if day.status == DayStatus.CLOSED.value:
            raise DayClosingError("اليوم الحالي مُقفل؛ لا يمكن تسجيل عمليات جديدة.")
        return day.id

    def is_day_closed(self, day_id: int) -> bool:
        row = self._repo.find_by_id(day_id)
        return row is not None and row["status"] == DayStatus.CLOSED.value

    def compute_expected_cash(self, day: DayClosing) -> float:
        """النقد المتوقع = رصيد الافتتاح + صافي حركة الخزينة لليوم."""
        return day.opening_balance + self._repo.treasury_net_for_day(day.id)

    def close_day(
        self, counted_cash: float, closed_by: int, notes: str | None = None
    ) -> DayClosing:
        day = self.get_or_open_today()
        if day.status == DayStatus.CLOSED.value:
            raise DayClosingError("اليوم مُقفل بالفعل.")

        expected = self.compute_expected_cash(day)
        difference = counted_cash - expected
        self._repo.close_day(
            day_id=day.id,
            expected_cash=expected,
            counted_cash=counted_cash,
            difference=difference,
            closed_by=closed_by,
            closed_at=now_iso(),
            notes=notes,
        )
        self._audit.log(
            "day_close",
            user_id=closed_by,
            entity="day_closings",
            entity_id=day.id,
            details=f"expected={expected:.2f} counted={counted_cash:.2f} "
            f"diff={difference:.2f}",
        )
        return DayClosing.from_row(self._repo.find_by_id(day.id))

    def reopen_day(self, day_id: int, user_id: int) -> None:
        """إعادة فتح يوم مُقفل (تتطلب صلاحية day.reopen تُفحص في الواجهة)."""
        self._repo.set_status(day_id, DayStatus.OPEN.value)
        self._audit.log(
            "day_reopen", user_id=user_id, entity="day_closings", entity_id=day_id
        )
