"""Member 4 API integration uses trusted source data, never browser roles/prices."""
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.main import SAMPLE, create_app

def test_budget_api_uses_saved_request_and_authorised_catalogue(tmp_path):
    with TestClient(create_app(tmp_path/"db","fixture")) as client:
        rid=str(uuid4())
        assert client.post("/api/requests",json={"request_id":rid,"text":SAMPLE}).status_code==201
        assert client.post(f"/api/requests/{rid}/recommendations").status_code==200
        response=client.post("/api/member4/budget-filter",json={"request_id":rid})
        assert response.status_code==200
        result=response.json()
        assert result["budget"]=="30"
        assert [p["product_id"] for p in result["products"]]==["product-001"]
        assert client.post("/api/member4/budget-filter",json={"request_id":rid,"candidates":[]}).status_code==422

def test_budget_api_requires_published_saved_candidates(tmp_path):
    with TestClient(create_app(tmp_path/"db","fixture")) as client:
        rid=str(uuid4())
        assert client.post("/api/member4/budget-filter",json={"request_id":rid}).status_code==404
        client.post("/api/requests",json={"request_id":rid,"text":SAMPLE})
        assert client.post("/api/member4/budget-filter",json={"request_id":rid}).status_code==409

def test_availability_api_authorises_then_reads_real_inventory(tmp_path):
    with TestClient(create_app(tmp_path/"db","fixture",operator_token="operator")) as client:
        data={"product_ids":["product-001","product-004","product-005","product-006"]}
        assert client.post("/api/member4/availability-check",json=data).status_code==403
        response=client.post("/api/member4/availability-check",json=data,headers={"Authorization":"Bearer operator"})
        assert response.status_code==200
        assert [r["status"] for r in response.json()]==["Available","Unavailable","Unknown","Unknown"]

def test_member4_api_rejects_role_and_evidence_spoofing(tmp_path):
    with TestClient(create_app(tmp_path/"db","fixture",operator_token="operator")) as client:
        response=client.post("/api/member4/availability-check",json={"requester_role":"FounderOperator","lookups":[]})
        assert response.status_code==422
