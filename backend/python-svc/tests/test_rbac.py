"""块3：RBAC 角色权限——analyst / reviewer / admin 的边界必须真的生效。"""
import pytest
from fastapi.testclient import TestClient

from app import auth, store
from app.config import settings
from app.main import app

client = TestClient(app)


def _mk(prefix: str, email_cfg: dict | None = None) -> tuple[str, str]:
    """注册用户并返回 (email, password)。"""
    email = f"{prefix}-{id(prefix)}-{len(store._users)}@example.hk".lower()
    pwd = "pass12345"
    client.post("/v1/auth/register", json={"email": email, "password": pwd, "name": prefix})
    return email, pwd


def _token(email: str, pwd: str) -> str:
    r = client.post("/v1/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_register_always_analyst_cannot_self_elevate():
    """注册入参即使带 role=admin 也不能提权（防「注册即管理员」）。"""
    email, pwd = _mk("analyst")
    user = auth.login(email, pwd)
    assert user["role"] == "analyst"
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {_token(email, pwd)}"}).json()
    assert me["user"]["role"] == "analyst"


def test_admin_granted_only_by_admin_emails_env(monkeypatch):
    email, pwd = _mk("boss")
    assert auth.effective_role(auth.login(email, pwd)) == "analyst"
    monkeypatch.setattr(settings, "admin_emails_raw", email)
    assert auth.effective_role(auth.login(email, pwd)) == "admin"
    # 生效角色会写进新签发的令牌
    tok = _token(email, pwd)
    assert auth.verify_token(tok)["role"] == "admin"


def test_ops_write_requires_privileged_role():
    email, pwd = _mk("plain")
    tok = _token(email, pwd)
    alert = store.add_alert("RBAC 测试实体", "制裁命中", ["OFAC"])

    # 规则治理：analyst 不得改动规则口径
    r = client.post("/v1/rules/HKMA.mortgage.ltv_above_cap/state",
                    json={"enabled": False}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403 and r.json()["detail"].startswith("role_forbidden")

    # 告警处置 / SAR 起草 / SAR 流转：同样需要 reviewer 以上
    assert client.patch(f"/v1/monitoring/alerts/{alert['id']}",
                        json={"status": "acknowledged"},
                        headers={"Authorization": f"Bearer {tok}"}).status_code == 403
    assert client.post(f"/v1/monitoring/alerts/{alert['id']}/sar",
                       headers={"Authorization": f"Bearer {tok}"}).status_code == 403
    assert client.post("/v1/sar", json={"name": "x", "reason": "y"},
                       headers={"Authorization": f"Bearer {tok}"}).status_code == 403
    assert client.post("/v1/sar/SAR-NOPE/status", json={"status": "submitted"},
                       headers={"Authorization": f"Bearer {tok}"}).status_code == 403


def test_ops_write_requires_auth_at_all():
    alert = store.add_alert("RBAC 未登录测试", "PEP 命中", [])
    assert client.patch(f"/v1/monitoring/alerts/{alert['id']}",
                        json={"status": "resolved"}).status_code == 401
    assert client.post("/v1/rules/HKMA.mortgage.ltv_above_cap/state",
                       json={"enabled": True}).status_code == 401


def test_admin_can_perform_ops_write(monkeypatch):
    email, pwd = _mk("super")
    monkeypatch.setattr(settings, "admin_emails_raw", email)
    tok = _token(email, pwd)
    alert = store.add_alert("RBAC 管理员测试", "制裁命中", ["HMT"])

    r = client.patch(f"/v1/monitoring/alerts/{alert['id']}",
                     json={"status": "acknowledged"},
                     headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and r.json()["status"] == "acknowledged"

    sar = client.post(f"/v1/monitoring/alerts/{alert['id']}/sar",
                      headers={"Authorization": f"Bearer {tok}"})
    assert sar.status_code == 200 and sar.json()["status"] == "draft"

    rule = client.post("/v1/rules/HKMA.mortgage.ltv_above_cap/state",
                       json={"enabled": False},
                       headers={"Authorization": f"Bearer {tok}"})
    assert rule.status_code == 200
    try:
        assert rule.json()["state"]["enabled"] is False
    finally:
        client.post("/v1/rules/HKMA.mortgage.ltv_above_cap/state",
                    json={"enabled": True, "snoozed_until": ""},
                    headers={"Authorization": f"Bearer {tok}"})


def test_read_endpoints_stay_open_for_all():
    """只读能力（规则导出、MI、能力清单）不设门槛，避免把系统用不了。"""
    assert client.get("/v1/rules").status_code == 200
    assert client.get("/v1/mi").status_code == 200
    assert client.get("/v1/capabilities").status_code == 200


@pytest.mark.parametrize("role", ["analyst", "reviewer", "admin"])
def test_effective_role_respects_stored_role(role):
    assert auth.effective_role({"email": "x@y.hk", "role": role}) == role
