"""Shared products/sales tables and prototype data (report §4, Figure 4, Figure 5)."""
from datetime import date, timedelta
from decimal import Decimal
import json
import sqlite3
import time

from fastapi.testclient import TestClient
import pytest

from backend.main import create_app
from backend.models import SalesRecord
from backend.profit_margin import AnalysisOutcome, ProfitMarginScope, analyse_profit_margin
from backend.retail_data import (PROTOTYPE_PRODUCTS, PROTOTYPE_SALES, create_retail_tables,
                                 ensure_retail_data, load_products, load_sales, seed_prototype_data)

SEPTEMBER = dict(start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))


@pytest.fixture
def db(tmp_path):
    connection = sqlite3.connect(tmp_path / "retail.sqlite3")
    ensure_retail_data(connection)
    yield connection
    connection.close()


def test_startup_creates_tables_with_nullable_cost_only(tmp_path):
    path = tmp_path / "db"
    with TestClient(create_app(path, "fixture")):
        pass
    with sqlite3.connect(path) as connection:
        columns = {table: {row[1]: (row[2], row[3]) for row in connection.execute(f"PRAGMA table_info({table})")}
                   for table in ("products", "sales")}
    assert list(columns["products"]) == ["product_id", "name", "category", "price", "abv",
                                         "sweetness", "flavour_tags"]
    assert list(columns["sales"]) == ["sale_id", "product_id", "sale_date", "quantity",
                                      "selling_price", "cost"]
    assert columns["sales"]["cost"] == ("TEXT", 0)
    assert all(notnull for name, (_, notnull) in columns["sales"].items() if name not in ("sale_id", "cost"))


def test_prototype_data_is_seeded_once_across_restarts(tmp_path):
    path = tmp_path / "db"
    for _ in range(2):
        with TestClient(create_app(path, "fixture")):
            pass
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT count(*) FROM products").fetchone()[0] == len(PROTOTYPE_PRODUCTS)
        assert connection.execute("SELECT count(*) FROM sales").fetchone()[0] == len(PROTOTYPE_SALES)
        assert seed_prototype_data(connection) is False


def test_existing_data_is_never_mixed_with_prototype_rows(tmp_path):
    connection = sqlite3.connect(tmp_path / "db")
    create_retail_tables(connection)
    connection.execute("INSERT INTO products VALUES ('own-1', 'House Red', 'Wine', '9.99', '13', 'dry', '[]')")
    ensure_retail_data(connection)
    assert [p.product_id for p in load_products(connection)] == ["own-1"]
    assert load_sales(connection) == []


def test_money_is_stored_as_text_and_round_trips_exactly(db):
    db.execute("INSERT INTO sales (sale_date, product_id, quantity, selling_price, cost) "
               "VALUES ('2026-09-30', 'product-001', 3, '0.10', 0.07)")
    assert db.execute("SELECT count(*) FROM products WHERE typeof(price) != 'text'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM sales WHERE typeof(selling_price) != 'text' "
                      "OR (cost IS NOT NULL AND typeof(cost) != 'text')").fetchone()[0] == 0
    # The REAL literal 0.07 is converted to text by the column's TEXT affinity.
    [added] = [row for row in load_sales(db) if row["sale_date"] == "2026-09-30"]
    assert (added["selling_price"], added["cost"]) == ("0.10", "0.07")
    assert load_products(db)[0].price == Decimal("25.00")


def test_prototype_rows_follow_shared_contracts(db):
    products = load_products(db)
    assert {p.category for p in products} == {"Wine", "Beer", "Spirits"}
    assert products[0].flavour_tags == ["red", "plum", "oak"]
    known = {p.product_id for p in products}
    rows = load_sales(db)
    assert {row["sale_date"][:7] for row in rows} == {"2026-08", "2026-09", "2026-10"}
    assert [row for row in rows if row["cost"] is None] == [
        dict(sale_id=11, product_id="product-002", sale_date="2026-09-27", quantity=2,
             selling_price="32.00", cost=None)]
    for row in rows:
        assert row["product_id"] in known
        if row["cost"] is not None:
            SalesRecord.model_validate({k: v for k, v in row.items() if k != "sale_id"})
    # Figure 5 example sale is present unchanged.
    assert any(r["sale_date"] == "2026-09-16" and r["quantity"] == 2 and r["selling_price"] == "67.00"
               and r["cost"] == "52.00" for r in rows)


@pytest.mark.parametrize("scope,outcome,figures,missing_cost", [
    (dict(product_id="product-001", **SEPTEMBER), AnalysisOutcome.COMPLETE,
     ("99.00", "60.00", "39.00", "39.39"), 0),
    (dict(category="Wine", **SEPTEMBER), AnalysisOutcome.PARTIAL,
     ("129.00", "76.00", "53.00", "41.09"), 1),
])
def test_profit_margin_over_prototype_data(db, scope, outcome, figures, missing_cost):
    result = analyse_profit_margin(ProfitMarginScope(**scope), lambda: load_sales(db),
                                   lambda: load_products(db), today=date(2026, 10, 26))
    assert result.outcome == outcome
    assert (result.revenue, result.total_cost, result.profit,
            result.profit_margin_percent) == tuple(map(Decimal, figures))
    assert result.excluded_missing_cost == missing_cost


def test_standard_analysis_within_ten_seconds(db):
    """§6.3.2 target: SQLite load plus calculation over ~10,000 sales rows."""
    db.executemany(
        "INSERT INTO sales (sale_date, product_id, quantity, selling_price, cost) VALUES (?, ?, ?, ?, ?)",
        [((date(2026, 1, 1) + timedelta(days=i % 290)).isoformat(), PROTOTYPE_PRODUCTS[i % 6][0],
          1 + i % 5, PROTOTYPE_PRODUCTS[i % 6][3], "10.00") for i in range(10_000)])
    scope = ProfitMarginScope(category="Wine", start_date=date(2026, 1, 1), end_date=date(2026, 10, 25))
    started = time.perf_counter()
    result = analyse_profit_margin(scope, lambda: load_sales(db), lambda: load_products(db),
                                   today=date(2026, 10, 26))
    elapsed = time.perf_counter() - started
    in_scope = db.execute("SELECT count(*) FROM sales JOIN products USING (product_id) WHERE category = 'Wine' "
                          "AND sale_date BETWEEN '2026-01-01' AND '2026-10-25'").fetchone()[0]
    assert result.record_count + result.excluded_missing_cost == in_scope > 6000
    assert elapsed < 10, f"{elapsed:.2f}s"


def test_flavour_tags_stored_as_json_list(db):
    stored = db.execute("SELECT flavour_tags FROM products WHERE product_id='product-006'").fetchone()[0]
    assert json.loads(stored) == []
