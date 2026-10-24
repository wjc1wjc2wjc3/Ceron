"""邮箱验证码登录 / 注册 与 忘记密码重置流程测试。

未配置 SMTP 时邮件走「回显」通道，因此本地可完整验证闭环。
"""
import time

from fastapi.testclient import TestClient

from app import auth, store
from app.config import settings
from app.main import app

client = TestClient(app)


def _email(prefix="code"):
    return f"{prefix}-{time.time_ns()}@example.hk"


def _request_code(email: str):
    r = client.post("/v1/auth/email/code", json={"email": email, "purpose": "login"})
    assert r.status_code == 200, r.text
    return r.json()


def test_code_login_roundtrip_and_autoregister():
    email = _email()
    sent = _request_code(email)
    assert sent["sent"] is True and sent.get("dev_code"), sent

    # 验证码登录：邮箱不存在时自动建号
    r = client.post("/v1/auth/email/verify", json={"email": email, "code": sent["dev_code"]})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == email
    assert store.get_user_by_email(email) is not None


def test_wrong_code_rejected():
    email = _email()
    _request_code(email)
    r = client.post("/v1/auth/email/verify", json={"email": email, "code": "000000"})
    assert r.status_code == 400 and r.json()["detail"] == "code_invalid"


def test_code_is_single_use():
    email = _email()
    code = _request_code(email)["dev_code"]
    assert client.post("/v1/auth/email/verify",
                       json={"email": email, "code": code}).status_code == 200
    again = client.post("/v1/auth/email/verify", json={"email": email, "code": code})
    assert again.status_code == 400 and again.json()["detail"] == "code_invalid"


def test_resend_throttled():
    email = _email()
    _request_code(email)
    second = _request_code(email)
    assert second["sent"] is True
    assert second["resend_wait"] > 0  # 冷却期内不发新码


def test_invalid_email_rejected():
    r = client.post("/v1/auth/email/code", json={"email": "not-an-email"})
    assert r.status_code == 400 and r.json()["detail"] == "email_invalid"


def test_password_reset_flow():
    email = _email("reset")
    client.post("/v1/auth/register", json={"email": email, "password": "old-pass-123"})
    assert client.post("/v1/auth/login",
                       json={"email": email, "password": "old-pass-123"}).status_code == 200

    forgot = client.post("/v1/auth/password/forgot", json={"email": email}).json()
    assert forgot["ok"] is True and forgot.get("dev_link")
    token = forgot["dev_link"].split("token=")[-1]

    bad = client.post("/v1/auth/password/reset", json={"token": token, "new_password": "short"})
    assert bad.status_code == 400 and bad.json()["detail"] == "password_too_short"

    ok = client.post("/v1/auth/password/reset", json={"token": token, "new_password": "new-pass-123"})
    assert ok.status_code == 200 and ok.json()["ok"] is True

    # 新密码可用，旧密码失效
    assert client.post("/v1/auth/login",
                       json={"email": email, "password": "new-pass-123"}).status_code == 200
    assert client.post("/v1/auth/login",
                       json={"email": email, "password": "old-pass-123"}).status_code == 401

    # 令牌一次性
    replay = client.post("/v1/auth/password/reset", json={"token": token, "new_password": "x1234567"})
    assert replay.status_code == 400 and replay.json()["detail"] == "token_invalid_or_expired"


def test_forgot_unknown_email_does_not_leak():
    r = client.post("/v1/auth/password/forgot", json={"email": _email("ghost")})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert "dev_link" not in r.json()  # 不存在的邮箱不发信也不回显


def test_reset_token_invalid():
    r = client.post("/v1/auth/password/reset", json={"token": "bogus-token", "new_password": "whatever123"})
    assert r.status_code == 400 and r.json()["detail"] == "token_invalid_or_expired"


def test_expired_reset_token_rejected():
    email = _email("exp")
    client.post("/v1/auth/register", json={"email": email, "password": "pass12345"})
    link = client.post("/v1/auth/password/forgot", json={"email": email}).json()["dev_link"]
    token = link.split("token=")[-1]

    # 让取其过期：把记录的有效期提前 1 小时
    for p in store._password_resets:
        p["expires_at"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - 3600))
    r = client.post("/v1/auth/password/reset", json={"token": token, "new_password": "new-pass-123"})
    assert r.status_code == 400 and r.json()["detail"] == "token_invalid_or_expired"


def test_providers_endpoint_includes_email_code():
    body = client.get("/v1/auth/providers").json()["providers"]
    assert body["email"] is True and body["email_code"] is True


def test_code_hash_never_stored_in_plaintext():
    email = _email("hash")
    code = _request_code(email)["dev_code"]
    recs = store.live_email_codes(email, "login")
    assert recs and recs[0]["code_hash"] != code
    assert auth.verify_password(code, recs[0]["code_hash"])
