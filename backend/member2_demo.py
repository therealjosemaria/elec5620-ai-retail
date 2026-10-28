"""Isolated fixtures for the Member 2 UI; never pretend these are current stock."""
from datetime import date, datetime, timezone
from decimal import Decimal

from backend.models import InventoryItem, Product
from backend.restocking import CompletedSale, RestockingScope, SalesSnapshot, analyse_restocking

DEMO_NOW = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)


class DemoInventory:
    def lookup_stock(self, product_id: str) -> InventoryItem:
        quantity, threshold = {"demo-red": (2, 10), "demo-white": (2, 10), "demo-beer": (15, 10)}[product_id]
        return InventoryItem(inventory_id="demo-store", product_id=product_id,
                             stock_quantity=quantity, reorder_threshold=threshold, last_updated=DEMO_NOW)


def demo_restocking(scope: RestockingScope):
    products = [Product(product_id=pid, name=name, category=category, price=Decimal("20"),
                        abv=Decimal("5"), sweetness="dry")
                for pid, name, category in [("demo-red", "Demo red wine", "Wine"),
                                            ("demo-white", "Demo white wine", "Wine"),
                                            ("demo-beer", "Demo beer", "Beer")]]
    snapshot = SalesSnapshot(start_date=date(2026, 10, 1), end_date=date(2026, 10, 26),
                             updated_at=DEMO_NOW, complete=True,
                             records=[CompletedSale(product_id=p.product_id, sale_date=date(2026, 10, 20), quantity=20)
                                      for p in products])
    result = analyse_restocking(scope, authorise=lambda _: True, load_catalogue=lambda: products,
                                inventory=DemoInventory(), load_sales=lambda: snapshot, now=DEMO_NOW)
    return result.model_copy(update={"data_mode": "fixture", "limitations": [*result.limitations,
        "Fixed demonstration data and clock (2026-10-27); not current inventory or real operator authentication."]})
