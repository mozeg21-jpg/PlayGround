"""Database layer for the sweets factory management system.
SQLite only (stdlib). Works on Termux / Android without extra deps.
"""
import os
import sqlite3
from datetime import datetime

# DB file lives next to this script. Simplest choice so Termux path stays short.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "factory.db")


def get_connection():
    """Return a new SQLite connection with FK enforcement and Row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create all tables if they do not exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            weight TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            required_qty INTEGER NOT NULL CHECK (required_qty >= 0),
            done_qty INTEGER NOT NULL DEFAULT 0 CHECK (done_qty >= 0),
            due_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'جاري التنفيذ',
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL CHECK (category IN ('خامات', 'كراتين', 'عبوات', 'قطع غيار', 'أخرى')),
            description TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 0 CHECK (qty >= 0),
            status TEXT NOT NULL DEFAULT 'مفتوح' CHECK (status IN ('مفتوح', 'محلول')),
            reported_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            required REAL NOT NULL DEFAULT 0 CHECK (required >= 0),
            received REAL NOT NULL DEFAULT 0 CHECK (received >= 0),
            created_at TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL CHECK (qty >= 0),
            loaded_qty INTEGER NOT NULL DEFAULT 0 CHECK (loaded_qty >= 0),
            scheduled_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'جاري التجهيز'
                CHECK (status IN ('جاري التجهيز', 'جاهز', 'تم تحميل جزء', 'تم التحميل بالكامل')),
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            telegram_id TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT 'موظف' CHECK (role IN ('مدير', 'موظف'))
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            action TEXT NOT NULL,
            ref_id INTEGER,
            qty INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
        );
    """)

    conn.commit()
    conn.close()


def clear_all():
    """Delete all rows (dev/test helper). Keeps schema."""
    conn = get_connection()
    cur = conn.cursor()
    for table in ("activity_log", "shipments", "materials", "incidents",
                  "orders", "employees", "products"):
        cur.execute(f"DELETE FROM {table};")
    conn.commit()
    conn.close()


def seed_demo_data():
    """Insert demo data: 3 products, 2 employees, 2 orders, 1 incident, 1 shipment."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cur = conn.cursor()

    # Skip seeding if products already exist (idempotent).
    cur.execute("SELECT COUNT(*) FROM products;")
    if cur.fetchone()[0] > 0:
        conn.close()
        return False

    # --- Products: 3 demo items ---
    cur.execute("INSERT INTO products (name, type, weight) VALUES (?, ?, ?);",
                ("بسبوسة", "حلويات شرقية", "1 كجم"))
    p1 = cur.lastrowid
    cur.execute("INSERT INTO products (name, type, weight) VALUES (?, ?, ?);",
                ("كنافة", "حلويات شرقية", "500 جم"))
    p2 = cur.lastrowid
    cur.execute("INSERT INTO products (name, type, weight) VALUES (?, ?, ?);",
                ("معمول تمر", "معجنات", "750 جم"))
    p3 = cur.lastrowid

    # --- Employees: 1 manager + 1 worker (needed for activity_log FK) ---
    cur.execute("INSERT INTO employees (name, telegram_id, role) VALUES (?, ?, ?);",
                ("المدير", "", "مدير"))
    manager_id = cur.lastrowid
    cur.execute("INSERT INTO employees (name, telegram_id, role) VALUES (?, ?, ?);",
                ("أحمد (عامل)", "", "موظف"))
    worker_id = cur.lastrowid

    # --- Orders: 2 production orders (remaining = required - done, computed later) ---
    cur.execute(
        "INSERT INTO orders (product_id, required_qty, done_qty, due_time, status)"
        " VALUES (?, ?, ?, ?, ?);",
        (p1, 200, 50, "2026-10-09 12:00:00", "جاري التنفيذ"))
    cur.execute(
        "INSERT INTO orders (product_id, required_qty, done_qty, due_time, status)"
        " VALUES (?, ?, ?, ?, ?);",
        (p2, 150, 0, "2026-10-09 17:00:00", "جاري التنفيذ"))

    # --- Materials: 2 rows (optional but useful for later steps) ---
    cur.execute("INSERT INTO materials (name, required, received, created_at)"
                " VALUES (?, ?, ?, ?);", ("سكر", 100, 60, now))
    cur.execute("INSERT INTO materials (name, required, received, created_at)"
                " VALUES (?, ?, ?, ?);", ("دقيق", 80, 80, now))

    # --- Incidents: 1 open shortage ---
    cur.execute(
        "INSERT INTO incidents (category, description, qty, status, reported_by, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?);",
        ("خامات", "نقص سكر للحشو", 20, "مفتوح", "أحمد (عامل)", now))

    # --- Shipments: 1 truck ---
    cur.execute(
        "INSERT INTO shipments (product_id, qty, loaded_qty, scheduled_time, status)"
        " VALUES (?, ?, ?, ?, ?);",
        (p1, 200, 0, "2026-10-09 18:00:00", "جاري التجهيز"))

    # --- Activity log: 1 sample row so GET /api/activity is not empty ---
    cur.execute(
        "INSERT INTO activity_log (employee_id, action, ref_id, qty, created_at)"
        " VALUES (?, ?, ?, ?, ?);",
        (worker_id, "بدء أمر إنتاج", 1, 50, now))

    conn.commit()
    conn.close()
    return True


if __name__ == "__main__":
    init_db()
    seeded = seed_demo_data()
    conn = get_connection()
    cur = conn.cursor()
    print("seeded:" , seeded)
    for table in ("products", "orders", "incidents", "materials",
                  "shipments", "employees", "activity_log"):
        cur.execute(f"SELECT COUNT(*) AS c FROM {table};")
        print(table, cur.fetchone()["c"])
    # Show remaining is computed, not stored: required - done
    cur.execute("SELECT id, required_qty, done_qty, (required_qty - done_qty) AS remaining"
                " FROM orders;")
    for row in cur.fetchall():
        print("order", dict(row))
    conn.close()
