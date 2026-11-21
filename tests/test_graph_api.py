"""Graph + API loop: CR -> assessment -> CAB decision -> outcome (PIR)."""

from fastapi.testclient import TestClient

from changeguard import store as store_mod
from changeguard.api import app
from changeguard.graph import ORDER

client = TestClient(app)


def test_graph_order():
    assert ORDER == ["collect", "retrieve", "features", "score", "explain", "critic"]


def test_full_loop_via_api(monkeypatch, history):
    import changeguard.graph as g
    monkeypatch.setattr(g, "load_history", lambda p: history)
    store_mod.clear()
    r = client.post("/assessments", json={
        "title": "Index rebuild", "description": "rebuild", "ci": "orders-db",
        "change_type": "normal", "scheduled_at": "2025-03-14T22:30:00",
        "requester": "rel-eng-01", "rollback_plan_present": False,
        "rollback_plan_tested": False, "test_evidence": False})
    assert r.status_code == 200, r.text
    body = r.json()
    rid = body["id"]
    assert body["decision"] == "pending"
    assert body["assessment"]["lane"] in ("standard", "needs-CAB", "reject-back")
    assert client.get(f"/assessments/{rid}").status_code == 200
    assert client.post(f"/assessments/{rid}/request-info", json={"comment": "attach logs"}).json()["decision"] == "needs-info"
    assert client.post(f"/assessments/{rid}/approve", json={"comment": "ok"}).json()["decision"] == "approved"
    assert client.post(f"/assessments/{rid}/outcome", json={"outcome": "success"}).json()["outcome"] == "success"
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
