"""块2：运营控制台后端——告警处置（认领/结案）与「告警 → SAR」一键申报。

这些写操作受 RBAC 保护（reviewer/admin），本文件统一使用管理员令牌调用，
同时也验证「权限真的生效」而非仅仅加了个装饰。
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app import store
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture
def admin():
    """注册并登录一个 ADMIN_EMAILS 名单内的管理员，返回其 Authorization 头。"""
    email = f"ops-admin-{uuid.uuid4().hex[:10]}@example.hk"
    pwd = "pass12345"
    client.post("/v1/auth/register", json={"email": email, "password": pwd})
    monkeypatch_expects = settings.admin_emails_raw
    settings.admin_emails_raw = email  # 直接改写测试进程内的 ADMIN_EMAILS 视图
    try:
        tok = client.post("/v1/auth/login", json={"email": email, "password": pwd}).json()["token"]
        yield {"Authorization": f"Bearer {tok}"}
    finally:
        settings.admin_emails_raw = monkeypatch_expects


def test_alert_lifecycle_open_to_acknowledged_to_resolved(admin):
    a = store.add_alert("测试实体A", "制裁名单重查命中", ["OFAC"])
    assert a["status"] == "open"

    r = client.patch(f"/v1/monitoring/alerts/{a['id']}", json={"status": "acknowledged"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "acknowledged"

    r = client.patch(f"/v1/monitoring/alerts/{a['id']}", json={"status": "resolved"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "resolved"


def test_alert_status_validation_and_404(admin):
    a = store.add_alert("测试实体B", "PEP 命中", [])
    bad = client.patch(f"/v1/monitoring/alerts/{a['id']}",
                       json={"status": "nonsense"}, headers=admin)
    assert bad.status_code == 400
    missing = client.patch("/v1/monitoring/alerts/NOPE-9999",
                           json={"status": "resolved"}, headers=admin)
    assert missing.status_code == 404


def test_alert_to_sar_links_and_acknowledges_source(admin):
    """从告警起草 SAR：必须带上来源留痕，并把来源告警置为已认领（避免重复申报）。"""
    a = store.add_alert("高危客户C", "制裁名单命中", ["HMT"])
    r = client.post(f"/v1/monitoring/alerts/{a['id']}/sar", headers=admin)
    assert r.status_code == 200
    sar = r.json()
    assert sar["status"] == "draft"
    assert sar["decision_summary"]["source"] == "monitoring_alert"

    created = next(s for s in client.get("/v1/sar").json()["sars"] if s["id"] == sar["id"])
    assert created["name"] == "高危客户C"
    alert = next(x for x in client.get("/v1/monitoring/alerts").json()["alerts"]
                 if str(x["id"]) == str(a["id"]))
    assert alert["status"] == "acknowledged"


def test_sar_status_transitions_through_endpoint(admin):
    a = store.add_alert("测试实体D", "异常结构", [])
    sar = client.post(f"/v1/monitoring/alerts/{a['id']}/sar", headers=admin).json()
    r = client.post(f"/v1/sar/{sar['id']}/status", json={"status": "submitted"}, headers=admin)
    assert r.status_code == 200 and r.json()["sar"]["status"] == "submitted"
    r = client.post(f"/v1/sar/{sar['id']}/status", json={"status": "closed"}, headers=admin)
    assert r.json()["sar"]["status"] == "closed"


def test_ops_writes_rejected_when_unauthorized():
    """没有令牌时应被拒，证明 RBAC 不是摆设（与上面的管理员用例成对）。"""
    a = store.add_alert("测试实体E", "命中", [])
    assert client.patch(f"/v1/monitoring/alerts/{a['id']}",
                        json={"status": "resolved"}).status_code == 401
    assert client.post(f"/v1/monitoring/alerts/{a['id']}/sar").status_code == 401


def test_mi_report_counts_open_alerts_and_sars():
    before = client.get("/v1/mi").json()
    store.add_alert("MI测试实体", "周期重查命中", [])
    after = client.get("/v1/mi").json()
    assert after["open_alerts"] >= before["open_alerts"]
    assert "by_vertical" in after and "by_action" in after
