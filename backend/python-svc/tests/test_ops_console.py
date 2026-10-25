"""块2：运营控制台后端——告警处置（认领/结案）与「告警 → SAR」一键申报。"""
from fastapi.testclient import TestClient

from app import store
from app.main import app

client = TestClient(app)


def test_alert_lifecycle_open_to_acknowledged_to_resolved():
    a = store.add_alert("测试实体A", "制裁名单重查命中", ["OFAC"])
    assert a["status"] == "open"

    r = client.patch(f"/v1/monitoring/alerts/{a['id']}", json={"status": "acknowledged"})
    assert r.status_code == 200 and r.json()["status"] == "acknowledged"

    r = client.patch(f"/v1/monitoring/alerts/{a['id']}", json={"status": "resolved"})
    assert r.status_code == 200 and r.json()["status"] == "resolved"


def test_alert_status_validation_and_404():
    a = store.add_alert("测试实体B", "PEP 命中", [])
    bad = client.patch(f"/v1/monitoring/alerts/{a['id']}", json={"status": "nonsense"})
    assert bad.status_code == 400
    missing = client.patch("/v1/monitoring/alerts/NOPE-9999", json={"status": "resolved"})
    assert missing.status_code == 404


def test_alert_to_sar_links_and_acknowledges_source():
    """从告警起草 SAR：必须带上来源留痕，并把来源告警置为已认领（避免重复申报）。"""
    a = store.add_alert("高危客户C", "制裁名单命中", ["HMT"])
    r = client.post(f"/v1/monitoring/alerts/{a['id']}/sar")
    assert r.status_code == 200
    sar = r.json()
    assert sar["status"] == "draft"
    assert sar["decision_summary"]["source"] == "monitoring_alert"

    listed = client.get("/v1/sar").json()["sars"]
    created = next(s for s in listed if s["id"] == sar["id"])
    assert created["name"] == "高危客户C"
    # 来源告警自动 ack
    alert = next(x for x in client.get("/v1/monitoring/alerts").json()["alerts"]
                 if str(x["id"]) == str(a["id"]))
    assert alert["status"] == "acknowledged"


def test_sar_status_transitions_through_endpoint():
    a = store.add_alert("测试实体D", "异常结构", [])
    sar = client.post(f"/v1/monitoring/alerts/{a['id']}/sar").json()
    r = client.post(f"/v1/sar/{sar['id']}/status", json={"status": "submitted"})
    assert r.status_code == 200 and r.json()["sar"]["status"] == "submitted"
    r = client.post(f"/v1/sar/{sar['id']}/status", json={"status": "closed"})
    assert r.json()["sar"]["status"] == "closed"


def test_mi_report_counts_open_alerts_and_sars():
    before = client.get("/v1/mi").json()
    assert before["open_alerts"] >= 0 and before["sars_total"] >= 0
    store.add_alert("MI测试实体", "周期重查命中", [])
    after = client.get("/v1/mi").json()
    assert after["open_alerts"] >= before["open_alerts"]
    assert "by_vertical" in after and "by_action" in after
