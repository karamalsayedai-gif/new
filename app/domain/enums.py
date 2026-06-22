"""تعدادات نطاق العمل (قيم نصّية تُخزَّن كما هي في قاعدة البيانات)."""
from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # noqa: D401
        return self.value


class SaleType(StrEnum):
    CASH = "cash"
    INSTALLMENT = "installment"


class MotorcycleStatus(StrEnum):
    IN_STOCK = "in_stock"
    SOLD = "sold"
    RESERVED = "reserved"


class TreasuryDirection(StrEnum):
    IN = "in"
    OUT = "out"


class TreasuryCategory(StrEnum):
    SALE = "sale"
    INSTALLMENT = "installment"
    PURCHASE = "purchase"
    EXPENSE = "expense"
    INCOME = "income"
    MANUAL = "manual"


class DayStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class InstallmentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    LATE = "late"


class ItemStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class StockDirection(StrEnum):
    IN = "in"
    OUT = "out"
