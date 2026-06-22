"""أدوات تنسيق العملة والتاريخ والأرقام للسوق المصري."""
from __future__ import annotations

from datetime import date, datetime


def format_currency(value: float, symbol: str = "ج.م") -> str:
    return f"{value:,.2f} {symbol}"


def format_number(value: float) -> str:
    return f"{value:,.2f}"


def format_date(dt: datetime | date) -> str:
    return dt.strftime("%Y/%m/%d")


def format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y/%m/%d %H:%M")


def business_date_key(dt: datetime | date) -> str:
    """مفتاح اليوم المستخدم في الإقفال اليومي (بدون وقت)."""
    return dt.strftime("%Y-%m-%d")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
