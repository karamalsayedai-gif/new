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
class Purchase:
    id: int
    supplier_id: int
    total: float
    paid: float
    date: str
    day_id: int | None = None
    user_id: int | None = None
    notes: str = ""
    supplier_name: str = ""

    @property
    def remaining(self) -> float:
        return self.total - self.paid

    @staticmethod
    def from_row(row: Mapping) -> "Purchase":
        keys = row.keys()
        return Purchase(
            id=row["id"],
            supplier_id=row["supplier_id"],
            total=row["total"] or 0.0,
            paid=row["paid"] or 0.0,
            date=row["date"] or "",
            day_id=row["day_id"],
            user_id=row["user_id"],
            notes=row["notes"] or "",
            supplier_name=row["supplier_name"] if "supplier_name" in keys else "",
        )


@dataclass
class PurchaseItem:
    id: int
    purchase_id: int
    item_id: int | None
    description: str
    quantity: float
    unit_cost: float

    @property
    def line_total(self) -> float:
        return self.quantity * self.unit_cost

    @staticmethod
    def from_row(row: Mapping) -> "PurchaseItem":
        return PurchaseItem(
            id=row["id"],
            purchase_id=row["purchase_id"],
            item_id=row["item_id"],
            description=row["description"],
            quantity=row["quantity"] or 0.0,
            unit_cost=row["unit_cost"] or 0.0,
        )


@dataclass
class Sale:
    id: int
    customer_id: int | None
    type: str
    total: float
    discount: float
    paid: float
    date: str
    day_id: int | None = None
    user_id: int | None = None
    notes: str = ""
    customer_name: str = ""

    @property
    def remaining(self) -> float:
        return self.total - self.paid

    @property
    def payment_status(self) -> str:
        if self.remaining <= 0:
            return "مدفوعة"
        if self.paid <= 0:
            return "آجل"
        return "جزئي"

    @staticmethod
    def from_row(row: Mapping) -> "Sale":
        keys = row.keys()
        return Sale(
            id=row["id"],
            customer_id=row["customer_id"],
            type=row["type"],
            total=row["total"] or 0.0,
            discount=(row["discount"] if "discount" in keys else 0.0) or 0.0,
            paid=row["paid"] or 0.0,
            date=row["date"] or "",
            day_id=row["day_id"],
            user_id=row["user_id"],
            notes=row["notes"] or "",
            customer_name=row["customer_name"] if "customer_name" in keys else "",
        )


@dataclass
class SaleItem:
    id: int
    sale_id: int
    item_id: int | None
    description: str
    quantity: float
    unit_price: float

    @property
    def line_total(self) -> float:
        return self.quantity * self.unit_price

    @staticmethod
    def from_row(row: Mapping) -> "SaleItem":
        return SaleItem(
            id=row["id"],
            sale_id=row["sale_id"],
            item_id=row["item_id"],
            description=row["description"],
            quantity=row["quantity"] or 0.0,
            unit_price=row["unit_price"] or 0.0,
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
