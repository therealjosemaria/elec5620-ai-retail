"""Shared SQLite tables for Product and SalesRecord (report §4, Figure 4).

Created at startup and seeded with prototype data only when both tables are empty,
so existing local data is never overwritten or mixed with sample rows. Feature code
should read through these loaders rather than defining its own tables.

Money is stored as decimal text (TEXT affinity, never REAL) so values stay exact.
selling_price and cost are per-unit values (docs/uc-m3-02-profit-margin.md); cost
may be NULL to represent a sale without cost data (report §10.6, 3a).
"""
import json
import sqlite3

from backend.models import Product

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
    price TEXT NOT NULL, abv TEXT NOT NULL, sweetness TEXT NOT NULL,
    flavour_tags TEXT NOT NULL DEFAULT '[]'
);
-- REFERENCES documents the association; SQLite enforces it only with
-- PRAGMA foreign_keys=ON, which the shared connection does not enable.
CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    sale_date TEXT NOT NULL, quantity INTEGER NOT NULL,
    selling_price TEXT NOT NULL, cost TEXT
);
"""

# product_id style and the 2026-09-16 vodka sale follow the Figure 5 object diagram.
PROTOTYPE_PRODUCTS = [
    ("product-001", "Shiraz 750ml", "Wine", "25.00", "14.5", "dry", ["red", "plum", "oak"]),
    ("product-002", "Pinot Noir 750ml", "Wine", "32.00", "13.0", "dry", ["red", "cherry", "light"]),
    ("product-003", "Sauvignon Blanc 750ml", "Wine", "18.00", "12.5", "dry", ["white", "citrus"]),
    ("product-004", "Moscato 750ml", "Wine", "15.00", "7.5", "sweet", ["white", "sparkling", "fruity"]),
    ("product-005", "Pale Ale 6-pack", "Beer", "22.00", "4.8", "dry", ["hoppy", "citrus"]),
    ("product-006", "Premium Vodka 700ml", "Spirits", "65.00", "40.0", "N/A", []),
]
PROTOTYPE_SALES = [
    ("2026-08-03", "product-001", 2, "25.00", "15.00"),
    ("2026-08-09", "product-003", 3, "18.00", "10.50"),
    ("2026-08-15", "product-005", 4, "22.00", "14.00"),
    ("2026-08-21", "product-002", 1, "32.00", "20.00"),
    ("2026-08-28", "product-006", 1, "65.00", "50.00"),
    ("2026-09-04", "product-001", 3, "25.00", "15.00"),
    ("2026-09-10", "product-004", 2, "15.00", "8.00"),
    ("2026-09-16", "product-006", 2, "67.00", "52.00"),
    ("2026-09-20", "product-005", 6, "21.00", "14.00"),
    ("2026-09-25", "product-001", 1, "24.00", "15.00"),
    ("2026-09-27", "product-002", 2, "32.00", None),  # Demonstrates missing cost (3a).
    ("2026-10-02", "product-003", 2, "18.00", "10.50"),
    ("2026-10-08", "product-001", 4, "25.00", "15.50"),
    ("2026-10-12", "product-005", 5, "22.00", "14.00"),
    ("2026-10-18", "product-002", 1, "31.00", "20.00"),
    ("2026-10-22", "product-006", 1, "65.00", "52.00"),
]


def create_retail_tables(db: sqlite3.Connection):
    db.executescript(SCHEMA)


def seed_prototype_data(db: sqlite3.Connection) -> bool:
    """Insert prototype rows only into empty tables; return whether rows were added."""
    if db.execute("SELECT EXISTS(SELECT 1 FROM products) OR EXISTS(SELECT 1 FROM sales)").fetchone()[0]:
        return False
    db.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
                   [(*row[:6], json.dumps(row[6])) for row in PROTOTYPE_PRODUCTS])
    db.executemany("INSERT INTO sales (sale_date, product_id, quantity, selling_price, cost) "
                   "VALUES (?, ?, ?, ?, ?)", PROTOTYPE_SALES)
    return True


def ensure_retail_data(db: sqlite3.Connection):
    create_retail_tables(db)
    seed_prototype_data(db)


def _rows(db, query):
    # Plain dicts regardless of the connection's row_factory.
    cursor = db.execute(query)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor]


def load_products(db: sqlite3.Connection) -> list[Product]:
    return [Product.model_validate({**row, "flavour_tags": json.loads(row["flavour_tags"])})
            for row in _rows(db, "SELECT * FROM products ORDER BY product_id")]


def load_sales(db: sqlite3.Connection) -> list[dict]:
    """Raw rows; cost may be None. Validation belongs to the consuming feature."""
    return _rows(db, "SELECT sale_id, product_id, sale_date, quantity, selling_price, cost "
                     "FROM sales ORDER BY sale_date, sale_id")
