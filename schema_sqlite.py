# Python 3.9+ | File: schema_sqlite.py | Target: Mobile POS Full Database Schema & ORM
"""
Expanded SQLite relational schema and ORM mapper matching the Mobile POS domain entities.
Contains definitions for Users, Categories, Products, Discounts, Fees, Transactions, and Stock Opname.
"""

from __future__ import annotations
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('owner', 'staff', 'cashier')) NOT NULL DEFAULT 'staff',
    name TEXT,
    phone TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS store_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    business_type TEXT DEFAULT 'F&B',
    address TEXT,
    phone TEXT,
    email TEXT,
    currency TEXT DEFAULT 'IDR',
    receipt_footer TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_name TEXT NOT NULL,
    status TEXT CHECK(status IN ('ACTIVE', 'EXPIRED', 'TRIAL')) NOT NULL DEFAULT 'ACTIVE',
    expires_at TIMESTAMP,
    max_outlets INTEGER DEFAULT 1,
    max_staff INTEGER DEFAULT 10,
    features_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    barcode TEXT UNIQUE,
    price REAL NOT NULL,
    cost REAL DEFAULT 0.0,
    stock INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    percentage REAL DEFAULT 0.0,
    fixed_amount REAL DEFAULT 0.0,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS additional_fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    percentage REAL DEFAULT 0.0,
    fixed_amount REAL DEFAULT 0.0,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    invoice_number TEXT,
    total_cost REAL NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    cost_per_unit REAL NOT NULL,
    subtotal REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    subtotal REAL NOT NULL,
    tax REAL DEFAULT 0.0,
    discount_amount REAL DEFAULT 0.0,
    fee_amount REAL DEFAULT 0.0,
    total_amount REAL NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'CASH',
    cash_amount REAL DEFAULT 0.0,
    change_amount REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaction_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    subtotal REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_opnames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    physical_count INTEGER NOT NULL,
    system_count INTEGER NOT NULL,
    difference INTEGER NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    movement_type TEXT CHECK(movement_type IN ('SALE', 'RESTOCK', 'OPNAME_ADJUST', 'MANUAL')) NOT NULL,
    quantity INTEGER NOT NULL,
    reference_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_movements_prod ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_type ON stock_movements(movement_type);
CREATE INDEX IF NOT EXISTS idx_stock_movements_date ON stock_movements(created_at);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
"""


class Database:
    def __init__(self, db_path: str = "pos_database.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.executescript(SCHEMA_SQL)
            # Automatic schema migration for existing sqlite databases
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(users)")
            user_cols = [row[1] for row in cur.fetchall()]
            if "phone" not in user_cols:
                cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
            if "is_active" not in user_cols:
                cur.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")

            cur.execute("PRAGMA table_info(transactions)")
            columns = [row[1] for row in cur.fetchall()]
            if "total_amount" not in columns:
                cur.execute("ALTER TABLE transactions ADD COLUMN total_amount REAL DEFAULT 0.0")
            if "discount_amount" not in columns:
                cur.execute("ALTER TABLE transactions ADD COLUMN discount_amount REAL DEFAULT 0.0")
            if "fee_amount" not in columns:
                cur.execute("ALTER TABLE transactions ADD COLUMN fee_amount REAL DEFAULT 0.0")
            if "customer_id" not in columns:
                cur.execute("ALTER TABLE transactions ADD COLUMN customer_id INTEGER REFERENCES customers(id)")

    def seed_defaults(self) -> None:
        """Seed initial reference data if tables are empty."""
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM users")
            if cur.fetchone()[0] == 0:
                # Password hash for 'password123'
                default_hash = hashlib.sha256("password123".encode("utf-8")).hexdigest()
                cur.execute("""
                    INSERT INTO users (username, password_hash, role, name, phone)
                    VALUES 
                    ('admin', ?, 'owner', 'Store Owner', '081122334455'),
                    ('cashier1', ?, 'staff', 'Budi Staff', '081199887766')
                """, (default_hash, default_hash))

            cur.execute("SELECT COUNT(*) FROM store_profiles")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO store_profiles (name, business_type, address, phone, email, currency, receipt_footer)
                    VALUES ('Kasera Coffee & Bakery', 'F&B / Cafe', 'Jl. Thamrin No. 8, Jakarta Pusat', '0212345678', 'hello@kaserapos.id', 'IDR', 'Terima kasih atas kunjungan Anda!')
                """)

            cur.execute("SELECT COUNT(*) FROM subscriptions")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO subscriptions (plan_name, status, expires_at, max_outlets, max_staff, features_json)
                    VALUES ('Kasera Enterprise Pro', 'ACTIVE', '2028-12-31 23:59:59', 5, 25, '["kasera_pay", "inventory_advanced", "stock_opname", "multi_staff"]')
                """)

            cur.execute("SELECT COUNT(*) FROM categories")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO categories (name) VALUES ('Beverages'), ('Pastries'), ('Meals')")

            cur.execute("SELECT COUNT(*) FROM products")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO products (category_id, name, barcode, price, cost, stock)
                    VALUES 
                    (1, 'Espresso Single', '8991001', 18000.0, 8000.0, 50),
                    (1, 'Cappuccino', '8991002', 25000.0, 11000.0, 40),
                    (2, 'Butter Croissant', '8992001', 22000.0, 10000.0, 20)
                """)

            cur.execute("SELECT COUNT(*) FROM discounts")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO discounts (name, percentage, fixed_amount) VALUES ('Member 10%', 10.0, 0.0)")

            cur.execute("SELECT COUNT(*) FROM additional_fees")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO additional_fees (name, percentage, fixed_amount) VALUES ('Service Charge 5%', 5.0, 0.0)")

            cur.execute("SELECT COUNT(*) FROM customers")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO customers (name, phone, email, address)
                    VALUES 
                    ('Walk-in Customer', '081234567890', 'walkin@pos.local', 'Store front'),
                    ('Budi Santoso', '081298765432', 'budi@example.com', 'Jl. Sudirman No. 12')
                """)

            cur.execute("SELECT COUNT(*) FROM suppliers")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO suppliers (name, phone, email, address)
                    VALUES 
                    ('PT Kopi Prima Indonesia', '0215551234', 'sales@kopiprima.id', 'Kawasan Industri Jakarta'),
                    ('CV Bakery Ingredients', '0215559876', 'order@bakeryindo.com', 'Tangerang')
                """)

    def list_products(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT p.id, p.name, p.barcode, p.price, p.cost, p.stock, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
        """)
        return [dict(row) for row in cur.fetchall()]

    def list_categories(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, icon FROM categories")
        return [dict(row) for row in cur.fetchall()]

    def list_discounts(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, percentage, fixed_amount FROM discounts WHERE is_active = 1")
        return [dict(row) for row in cur.fetchall()]

    def list_additional_fees(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, percentage, fixed_amount FROM additional_fees WHERE is_active = 1")
        return [dict(row) for row in cur.fetchall()]

    def list_employees(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, username, role, name, phone, is_active, created_at FROM users ORDER BY id ASC")
        return [dict(row) for row in cur.fetchall()]

    def create_employee(self, username: str, password: str, name: str, phone: Optional[str] = None, role: str = "staff") -> int:
        pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO users (username, password_hash, role, name, phone)
                VALUES (?, ?, ?, ?, ?)
            """, (username, pw_hash, role, name, phone))
            return cur.lastrowid

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, username, role, name, phone, is_active, created_at
            FROM users
            WHERE username = ? AND password_hash = ? AND is_active = 1
        """, (username, pw_hash))
        row = cur.fetchone()
        return dict(row) if row else None

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        old_hash = hashlib.sha256(old_password.encode("utf-8")).hexdigest()
        new_hash = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT id FROM users WHERE id = ? AND password_hash = ?", (user_id, old_hash))
            if not cur.fetchone():
                return False
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            return True

    def get_store_profile(self) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, business_type, address, phone, email, currency, receipt_footer, updated_at FROM store_profiles LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else {}

    def update_store_profile(self, name: str, business_type: str, address: str, phone: str, email: str, receipt_footer: str) -> Dict[str, Any]:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE store_profiles
                SET name = ?, business_type = ?, address = ?, phone = ?, email = ?, receipt_footer = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (name, business_type, address, phone, email, receipt_footer))
            return self.get_store_profile()

    def get_subscription(self) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, plan_name, status, expires_at, max_outlets, max_staff, features_json, created_at FROM subscriptions LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else {}

    def list_customers(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, phone, email, address, created_at FROM customers ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]

    def create_customer(self, name: str, phone: Optional[str] = None, email: Optional[str] = None, address: Optional[str] = None) -> int:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO customers (name, phone, email, address)
                VALUES (?, ?, ?, ?)
            """, (name, phone, email, address))
            return cur.lastrowid

    def list_suppliers(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, phone, email, address, created_at FROM suppliers ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]

    def create_supplier(self, name: str, phone: Optional[str] = None, email: Optional[str] = None, address: Optional[str] = None) -> int:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO suppliers (name, phone, email, address)
                VALUES (?, ?, ?, ?)
            """, (name, phone, email, address))
            return cur.lastrowid

    def record_purchase(
        self,
        supplier_id: Optional[int],
        invoice_number: str,
        notes: str,
        items: List[Dict[str, Any]]
    ) -> int:
        total_cost = sum(float(item["quantity"]) * float(item["cost_per_unit"]) for item in items)
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO purchases (supplier_id, invoice_number, total_cost, notes)
                VALUES (?, ?, ?, ?)
            """, (supplier_id, invoice_number, total_cost, notes))
            purchase_id = cur.lastrowid

            for item in items:
                qty = int(item["quantity"])
                cost = float(item["cost_per_unit"])
                subtotal = qty * cost
                prod_id = int(item["product_id"])

                cur.execute("SELECT name FROM products WHERE id = ?", (prod_id,))
                prod = cur.fetchone()
                prod_name = prod["name"] if prod else f"Product #{prod_id}"

                cur.execute("""
                    INSERT INTO purchase_items (purchase_id, product_id, product_name, quantity, cost_per_unit, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (purchase_id, prod_id, prod_name, qty, cost, subtotal))

                # Increment product stock and update unit cost
                cur.execute("""
                    UPDATE products 
                    SET stock = stock + ?, cost = ?
                    WHERE id = ?
                """, (qty, cost, prod_id))

                # Log RESTOCK movement
                cur.execute("""
                    INSERT INTO stock_movements (product_id, movement_type, quantity, reference_id, notes)
                    VALUES (?, 'RESTOCK', ?, ?, ?)
                """, (prod_id, qty, purchase_id, f"Purchase restock {invoice_number}"))

            return purchase_id

    def list_purchases(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT p.id, p.supplier_id, s.name as supplier_name, p.invoice_number, 
                   p.total_cost, p.notes, p.created_at
            FROM purchases p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            ORDER BY p.id DESC
        """)
        purchases = [dict(row) for row in cur.fetchall()]
        for p in purchases:
            cur.execute("""
                SELECT product_id, product_name, quantity, cost_per_unit, subtotal
                FROM purchase_items WHERE purchase_id = ?
            """, (p["id"],))
            p["items"] = [dict(item) for item in cur.fetchall()]
        return purchases

    def record_transaction(
        self,
        subtotal: float,
        tax: float,
        discount_amount: float,
        fee_amount: float,
        total_amount: float,
        payment_method: str,
        cash_amount: float,
        change_amount: float,
        items: List[Dict[str, Any]],
        user_id: Optional[int] = None,
        customer_id: Optional[int] = None
    ) -> int:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO transactions (user_id, customer_id, subtotal, tax, discount_amount, fee_amount, total_amount, payment_method, cash_amount, change_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, customer_id, subtotal, tax, discount_amount, fee_amount, total_amount, payment_method, cash_amount, change_amount))
            tx_id = cur.lastrowid

            for item in items:
                cur.execute("""
                    INSERT INTO transaction_items (transaction_id, product_id, product_name, quantity, price, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tx_id, item["productId"], item["productName"], item["quantity"], item["price"], item["subtotal"]))

                # Deduct inventory stock
                cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["quantity"], item["productId"]))

                # Log SALE movement
                cur.execute("""
                    INSERT INTO stock_movements (product_id, movement_type, quantity, reference_id, notes)
                    VALUES (?, 'SALE', ?, ?, ?)
                """, (item["productId"], -int(item["quantity"]), tx_id, f"Sale transaction #{tx_id}"))

            return tx_id

    def perform_stock_opname(self, product_id: int, physical_count: int, notes: str = "") -> Dict[str, Any]:
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT stock, name FROM products WHERE id = ?", (product_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Product ID {product_id} not found")
            
            system_count = row["stock"]
            diff = physical_count - system_count

            cur.execute("""
                INSERT INTO stock_opnames (product_id, physical_count, system_count, difference, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, physical_count, system_count, diff, notes))
            opname_id = cur.lastrowid

            # Sync physical count
            cur.execute("UPDATE products SET stock = ? WHERE id = ?", (physical_count, product_id))

            # Log OPNAME_ADJUST movement
            cur.execute("""
                INSERT INTO stock_movements (product_id, movement_type, quantity, reference_id, notes)
                VALUES (?, 'OPNAME_ADJUST', ?, ?, ?)
            """, (product_id, diff, opname_id, f"Stock opname #{opname_id}: {notes}"))

            return {
                "id": opname_id,
                "product_id": product_id,
                "product_name": row["name"],
                "previous_stock": system_count,
                "new_stock": physical_count,
                "difference": diff
            }

    def list_stock_movements(self, product_id: Optional[int] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        query = """
            SELECT sm.id, sm.product_id, p.name as product_name, sm.movement_type, 
                   sm.quantity, sm.reference_id, sm.notes, sm.created_at
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
        """
        params = []
        if product_id:
            query += " WHERE sm.product_id = ?"
            params.append(product_id)
        query += " ORDER BY sm.id DESC"

        cur.execute(query, tuple(params))
        return [dict(row) for row in cur.fetchall()]

    def get_sales_summary(self) -> Dict[str, Any]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as total_orders,
                COALESCE(SUM(total_amount), 0.0) as gross_revenue,
                COALESCE(SUM(tax), 0.0) as total_tax,
                COALESCE(SUM(discount_amount), 0.0) as total_discounts
            FROM transactions
        """)
        summary = dict(cur.fetchone())

        cur.execute("""
            SELECT ti.product_name, SUM(ti.quantity) as units_sold, SUM(ti.subtotal) as total_sales
            FROM transaction_items ti
            GROUP BY ti.product_id
            ORDER BY units_sold DESC
            LIMIT 5
        """)
        summary["top_products"] = [dict(r) for r in cur.fetchall()]
        return summary

    def close(self) -> None:
        self.conn.close()


if __name__ == "__main__":
    db = Database("pos_database.db")
    db.seed_defaults()
    summary = db.get_sales_summary()
    print("Schema extended. Initial sales summary:", summary)
    db.close()
