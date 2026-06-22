"""كيانات النطاق كـ dataclasses خفيفة.

تُبنى من صفوف قاعدة البيانات (sqlite3.Row) عبر ``from_row`` وتنفصل تمامًا عن
تفاصيل التخزين.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass
class Role:
    id: int
    name: str
    is_system: bool = False
    permissions: set[str] = field(default_factory=set)

    @staticmethod
    def from_row(row: Mapping) -> "Role":
        return Role(
            id=row["id"],
            name=row["name"],
            is_system=bool(row["is_system"]),
        )


@dataclass
class User:
    id: int
    username: str
    full_name: str
    role_id: int
    is_active: bool = True
    role_name: str = ""
    permissions: set[str] = field(default_factory=set)

    def can(self, permission_code: str) -> bool:
        return permission_code in self.permissions

    @staticmethod
    def from_row(row: Mapping, permissions: set[str] | None = None) -> "User":
        return User(
            id=row["id"],
            username=row["username"],
            full_name=row["full_name"],
            role_id=row["role_id"],
            is_active=bool(row["is_active"]),
            role_name=row["role_name"] if "role_name" in row.keys() else "",
            permissions=permissions or set(),
        )


@dataclass
class Customer:
    id: int
    name: str
    phone: str = ""
    national_id: str = ""
    address: str = ""
    balance: float = 0.0
    credit_limit: float = 0.0
    created_at: str = ""

    @staticmethod
    def from_row(row: Mapping) -> "Customer":
        keys = row.keys()
        return Customer(
            id=row["id"],
            name=row["name"],
            phone=row["phone"] or "",
            national_id=row["national_id"] or "",
            address=row["address"] or "",
            balance=row["balance"] or 0.0,
            credit_limit=(row["credit_limit"] if "credit_limit" in keys else 0.0) or 0.0,
            created_at=row["created_at"] or "",
        )


@dataclass
class InventoryItem:
    id: int
    name: str
    category: str = ""
    unit: str = "قطعة"
    quantity: float = 0.0
    min_stock: float = 0.0
    unit_cost: float = 0.0
    sale_price: float = 0.0
    status: str = "active"
    created_at: str = ""

    @property
    def is_low(self) -> bool:
        return self.min_stock > 0 and self.quantity <= self.min_stock

    @staticmethod
    def from_row(row: Mapping) -> "InventoryItem":
        return InventoryItem(
            id=row["id"],
            name=row["name"],
            category=row["category"] or "",
            unit=row["unit"] or "قطعة",
            quantity=row["quantity"] or 0.0,
            min_stock=row["min_stock"] or 0.0,
            unit_cost=row["unit_cost"] or 0.0,
            sale_price=row["sale_price"] or 0.0,
            status=row["status"] or "active",
            created_at=row["created_at"] or "",
        )


@dataclass
class Supplier:
    id: int
    name: str
    phone: str = ""
    address: str = ""
    balance: float = 0.0
    created_at: str = ""

    @staticmethod
    def from_row(row: Mapping) -> "Supplier":
        return Supplier(
            id=row["id"],
            name=row["name"],
            phone=row["phone"] or "",
            address=row["address"] or "",
            balance=row["balance"] or 0.0,
            created_at=row["created_at"] or "",
        )


@dataclass
class DayClosing:
    id: int
    business_date: str
    opening_balance: float
    expected_cash: float
    counted_cash: float | None
    difference: float | None
    status: str
    opened_at: str
    closed_at: str | None = None
    closed_by: int | None = None
    notes: str | None = None

    @staticmethod
    def from_row(row: Mapping) -> "DayClosing":
        return DayClosing(
            id=row["id"],
            business_date=row["business_date"],
            opening_balance=row["opening_balance"],
            expected_cash=row["expected_cash"],
            counted_cash=row["counted_cash"],
            difference=row["difference"],
            status=row["status"],
            opened_at=row["opened_at"],
            closed_at=row["closed_at"],
            closed_by=row["closed_by"],
            notes=row["notes"],
        )
