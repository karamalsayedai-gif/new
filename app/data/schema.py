"""تعريف مخطط قاعدة البيانات (DDL) للإصدار الحالي.

عند تعديل المخطط لاحقًا تُضاف خطوات الترقية في ``migrations.py`` ويُزاد
``AppConfig.DB_SCHEMA_VERSION``.
"""
from __future__ import annotations

CREATE_STATEMENTS: list[str] = [
    # ── الأمن والصلاحيات ────────────────────────────────────────────────
    """
    CREATE TABLE roles (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL UNIQUE,
        is_system  INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE permissions (
        code        TEXT PRIMARY KEY,
        description TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE role_permissions (
        role_id         INTEGER NOT NULL,
        permission_code TEXT NOT NULL,
        PRIMARY KEY (role_id, permission_code),
        FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
        FOREIGN KEY (permission_code) REFERENCES permissions(code) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT NOT NULL UNIQUE,
        full_name     TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role_id       INTEGER NOT NULL,
        is_active     INTEGER NOT NULL DEFAULT 1,
        created_at    TEXT NOT NULL,
        last_login_at TEXT,
        FOREIGN KEY (role_id) REFERENCES roles(id)
    );
    """,
    # ── الإعدادات ───────────────────────────────────────────────────────
    """
    CREATE TABLE settings (
        key   TEXT PRIMARY KEY,
        value TEXT,
        type  TEXT NOT NULL DEFAULT 'string'
    );
    """,
    # ── الإقفال اليومي ──────────────────────────────────────────────────
    """
    CREATE TABLE day_closings (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        business_date   TEXT NOT NULL UNIQUE,
        opening_balance REAL NOT NULL DEFAULT 0,
        expected_cash   REAL NOT NULL DEFAULT 0,
        counted_cash    REAL,
        difference      REAL,
        status          TEXT NOT NULL DEFAULT 'open',
        opened_at       TEXT NOT NULL,
        closed_at       TEXT,
        closed_by       INTEGER,
        notes           TEXT,
        FOREIGN KEY (closed_by) REFERENCES users(id)
    );
    """,
    # ── الموردون والمشتريات ─────────────────────────────────────────────
    """
    CREATE TABLE suppliers (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        phone      TEXT,
        address    TEXT,
        balance    REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    """,
    # ── المخزون ─────────────────────────────────────────────────────────
    """
    CREATE TABLE motorcycles (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        brand       TEXT NOT NULL,
        model       TEXT NOT NULL,
        year        INTEGER,
        color       TEXT,
        chassis_no  TEXT UNIQUE,
        motor_no    TEXT,
        cost        REAL NOT NULL DEFAULT 0,
        price       REAL NOT NULL DEFAULT 0,
        status      TEXT NOT NULL DEFAULT 'in_stock',
        supplier_id INTEGER,
        created_at  TEXT NOT NULL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    );
    """,
    """
    CREATE TABLE inventory_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        category   TEXT,
        quantity   REAL NOT NULL DEFAULT 0,
        unit_cost  REAL NOT NULL DEFAULT 0,
        sale_price REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE purchases (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER NOT NULL,
        total       REAL NOT NULL DEFAULT 0,
        paid        REAL NOT NULL DEFAULT 0,
        date        TEXT NOT NULL,
        day_id      INTEGER,
        user_id     INTEGER,
        notes       TEXT,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
        FOREIGN KEY (day_id) REFERENCES day_closings(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,
    # ── العملاء ─────────────────────────────────────────────────────────
    """
    CREATE TABLE customers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        phone       TEXT,
        national_id TEXT,
        address     TEXT,
        balance     REAL NOT NULL DEFAULT 0,
        created_at  TEXT NOT NULL
    );
    """,
    # ── المبيعات ────────────────────────────────────────────────────────
    """
    CREATE TABLE sales (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        type        TEXT NOT NULL,
        total       REAL NOT NULL DEFAULT 0,
        paid        REAL NOT NULL DEFAULT 0,
        date        TEXT NOT NULL,
        day_id      INTEGER,
        user_id     INTEGER,
        notes       TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (day_id) REFERENCES day_closings(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,
    """
    CREATE TABLE sale_items (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id       INTEGER NOT NULL,
        motorcycle_id INTEGER,
        item_id       INTEGER,
        description   TEXT NOT NULL,
        quantity      REAL NOT NULL DEFAULT 1,
        unit_price    REAL NOT NULL DEFAULT 0,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY (motorcycle_id) REFERENCES motorcycles(id),
        FOREIGN KEY (item_id) REFERENCES inventory_items(id)
    );
    """,
    """
    CREATE TABLE installment_plans (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id      INTEGER NOT NULL UNIQUE,
        down_payment REAL NOT NULL DEFAULT 0,
        months       INTEGER NOT NULL DEFAULT 0,
        interest_pct REAL NOT NULL DEFAULT 0,
        total_amount REAL NOT NULL DEFAULT 0,
        status       TEXT NOT NULL DEFAULT 'active',
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE installments (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id     INTEGER NOT NULL,
        due_date    TEXT NOT NULL,
        amount      REAL NOT NULL DEFAULT 0,
        paid_amount REAL NOT NULL DEFAULT 0,
        paid_at     TEXT,
        status      TEXT NOT NULL DEFAULT 'pending',
        FOREIGN KEY (plan_id) REFERENCES installment_plans(id) ON DELETE CASCADE
    );
    """,
    # ── الخزينة والمصروفات/الإيرادات ────────────────────────────────────
    """
    CREATE TABLE treasury (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        direction TEXT NOT NULL,
        category  TEXT NOT NULL,
        amount    REAL NOT NULL DEFAULT 0,
        ref_table TEXT,
        ref_id    INTEGER,
        date      TEXT NOT NULL,
        day_id    INTEGER,
        user_id   INTEGER,
        notes     TEXT,
        FOREIGN KEY (day_id) REFERENCES day_closings(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,
    # ── سجل التدقيق ─────────────────────────────────────────────────────
    """
    CREATE TABLE audit_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        action     TEXT NOT NULL,
        entity     TEXT,
        entity_id  INTEGER,
        details    TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,
]

INDEX_STATEMENTS: list[str] = [
    "CREATE INDEX idx_sales_day ON sales(day_id);",
    "CREATE INDEX idx_sales_customer ON sales(customer_id);",
    "CREATE INDEX idx_treasury_day ON treasury(day_id);",
    "CREATE INDEX idx_installments_plan ON installments(plan_id);",
    "CREATE INDEX idx_audit_created ON audit_log(created_at);",
]
