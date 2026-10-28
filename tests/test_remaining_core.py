"""Remaining core acceptance paths; real SQLite/graphs with no model calls."""
from datetime import date, datetime, timedelta, timezone
import sqlite3
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.models import InventoryItem, Product
from backend.stock import InventoryLookupResult, LookupStatus
from backend.replenishment import evaluate_inventory
from backend.demand import DemandScope, analyse_demand

NOW=datetime(2026,10,28,0,0,tzinfo=timezone.utc)

def evidence(qty=3,threshold=10,status=LookupStatus.FOUND,**kwargs):
    item=InventoryItem(inventory_id="store",product_id="p",stock_quantity=qty,reorder_threshold=threshold,last_updated=kwargs.get("stamp",NOW))
    return InventoryLookupResult(product_id="p",status=status,item=item,reason="Stale evidence" if status==LookupStatus.STALE else None)

@pytest.mark.parametrize("qty,threshold,alert,ordered",[(3,10,True,17),(10,10,True,10),(0,8,True,16),(11,10,False,None),(0,0,True,0)])
def test_threshold_and_reorder_formula(qty,threshold,alert,ordered):
    data=[evidence(qty,threshold)]
    a=evaluate_inventory(data,now=NOW).items[0]
    r=evaluate_inventory(data,reorder=True,now=NOW).items[0]
    assert (a.status=="low_stock")==alert
    assert a.suggested_quantity is None
    assert r.suggested_quantity==ordered
    assert r.stock_quantity==qty and r.reorder_threshold==threshold

@pytest.mark.parametrize("record",[evidence(status=LookupStatus.STALE),evidence(-1),evidence(threshold=-1),evidence(stamp=NOW+timedelta(days=1)),evidence(stamp=NOW.replace(tzinfo=None))])
def test_unreliable_inventory_withheld(record):
    result=evaluate_inventory([record],reorder=True,now=NOW)
    assert result.outcome=="data_error" and result.items[0].suggested_quantity is None

def test_missing_reorder_rule_does_not_invent_quantity():
    result=evaluate_inventory([evidence()],reorder=True,rule_available=False,now=NOW)
    assert result.outcome=="partial" and result.items[0].status=="rule_unavailable"
    assert result.items[0].suggested_quantity is None

@pytest.fixture
def system(tmp_path):
    path=tmp_path/"db"
    with TestClient(create_app(path,"fixture",operator_token="operator")) as client:
        yield client,path,{"Authorization":"Bearer operator"}

def business_snapshot(path):
    with sqlite3.connect(path) as db:
        return {t:db.execute("SELECT * FROM "+t+" ORDER BY 1").fetchall() for t in ["products","sales","inventory","inventory_items"]}

@pytest.mark.parametrize("route",["low-stock-alerts","reorder-suggestions","demand-trends"])
def test_operator_access_required(system,route):
    client,path,_=system
    payload={"product_id":"product-001","start_date":"2026-09-01","end_date":"2026-09-30"} if route=="demand-trends" else {}
    assert client.post("/api/"+route,json=payload).status_code==403
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM workflow_runs").fetchone()[0]==0

def test_connected_alerts_reorder_evidence_and_read_only_storage(system):
    client,path,headers=system
    before=business_snapshot(path)
    ids={"product_ids":["product-001","product-002","product-003","product-004"]}
    a=client.post("/api/low-stock-alerts",json=ids,headers=headers).json()
    assert a["outcome"]=="presented"
    assert [i["product_id"] for i in a["items"] if i["status"]=="low_stock"]==["product-002","product-003","product-004"]
    r=client.post("/api/reorder-suggestions",json=ids,headers=headers).json()
    assert [i["suggested_quantity"] for i in r["items"]]==[None,10,17,16]
    assert any(t["sender"]=="inventory_procurement_agent" for t in r["trace"])
    assert client.get(f"/api/workflows/{r['workflow_id']}").status_code==403
    saved=client.get(f"/api/workflows/{r['workflow_id']}",headers=headers).json()
    assert saved["inventory_decision"]["items"]==r["items"]
    partial=client.post("/api/reorder-suggestions",json={},headers=headers).json()
    assert partial["outcome"]=="partial"
    assert all(i["suggested_quantity"] is None for i in partial["items"] if i["product_id"] in ["product-005","product-006"])
    assert before==business_snapshot(path)
    assert client.get("/api/status").json()["live_attempts_today"]==0

def test_no_alert_or_reorder_above_threshold(system):
    client,_,h=system
    for route in ["low-stock-alerts","reorder-suggestions"]:
        result=client.post("/api/"+route,json={"product_ids":["product-001"]},headers=h).json()
        assert result["outcome"]=="not_required"

def catalogue():
    return [Product(product_id="p",name="Product",category="Wine",price=Decimal(10),abv=Decimal(12),sweetness="dry")]

def scope():
    return DemandScope(product_id="p",start_date="2026-09-01",end_date="2026-09-30")

def sales(old=2,new=4):
    return [dict(product_id="p",sale_date="2026-08-02",quantity=old),dict(product_id="p",sale_date="2026-09-10",quantity=new)]

@pytest.mark.parametrize("old,new,trend",[(2,4,"increasing"),(4,2,"decreasing"),(3,3,"stable"),(0,3,"increasing"),(3,0,"decreasing")])
def test_adjacent_equal_periods_and_classification(old,new,trend):
    result=analyse_demand(scope(),load_sales=lambda:sales(old,new),load_catalogue=catalogue,today=NOW.date())
    assert result.outcome=="complete" and result.trend==trend
    assert result.comparison_start==date(2026,8,2) and result.comparison_end==date(2026,8,31)
    assert result.change==new-old
    if old==0: assert result.percent_change is None

def test_missing_comparison_is_unknown_not_zero():
    result=analyse_demand(scope(),load_sales=lambda:sales()[1:],load_catalogue=catalogue,today=NOW.date())
    assert result.outcome=="no_comparison" and result.units_sold==4 and result.comparison_units is None
    assert result.trend is None

@pytest.mark.parametrize("bad",[dict(product_id="p",sale_date="2026-09-15",quantity=-1),dict(product_id="p",sale_date="bad",quantity=1),dict(product_id="p",sale_date="2026-09-15",quantity="3"),dict(product_id=None,sale_date="2026-09-15",quantity=1)])
def test_incomplete_sales_withhold_trend(bad):
    result=analyse_demand(scope(),load_sales=lambda:sales()+[bad],load_catalogue=catalogue,today=NOW.date())
    assert result.outcome=="partial" and result.trend is None

def test_missing_rule_and_source_failures():
    result=analyse_demand(scope(),load_sales=sales,load_catalogue=catalogue,today=NOW.date(),rule_available=False)
    assert result.outcome=="rule_unavailable" and result.trend is None
    def broken():raise RuntimeError("private")
    result=analyse_demand(scope(),load_sales=broken,load_catalogue=catalogue,today=NOW.date())
    assert result.outcome=="source_unavailable" and "private" not in result.model_dump_json()

def test_connected_demand_counts_quantities_not_missing_costs(system):
    client,path,h=system
    before=business_snapshot(path)
    result=client.post("/api/demand-trends",json={"product_id":"product-001","start_date":"2026-09-01","end_date":"2026-09-30"},headers=h)
    assert result.status_code==200
    data=result.json()
    assert (data["units_sold"],data["comparison_units"],data["trend"])==(4,2,"increasing")
    assert all(t["sender"]!="inventory_procurement_agent" for t in data["trace"])
    assert before==business_snapshot(path)
    for payload in [dict(product_id="product-001",category="Wine",start_date="2026-09-01",end_date="2026-09-30"),dict(product_id="product-001",start_date="2026-09-30",end_date="2026-09-01")]:
        assert client.post("/api/demand-trends",json=payload,headers=h).json()["outcome"]=="invalid_scope"
