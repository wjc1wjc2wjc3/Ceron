"""认证测试：注册 / 登录 / 会话校验 / 第三方账号复用。

第三方 OAuth 的真实网络交互无法在此验证（需平台 App 凭证），此处只覆盖
本地可测的部分：口令哈希、签发与校验令牌、非法/过期令牌、社交账号 upsert。
"""
import time

import pytest
from fastapi.testclient import TestClient

from app import auth, store
from app.config import settings
from app.main import app

client = TestClient(app)


def _unique(prefix="auth"):
    return f"{prefix}-{time.time_ns()}@example.hk"


def test_password_hash_and_verify():
    h = auth.hash_password("secret12345")
    assert h.startswith("pbkdf2_sha256$")
    assert auth.verify_password("secret12345", h)
    assert not auth.verify_password("wrong-pass", h)
    assert not auth.verify_password("secret12345", None)


def test_register_login_and_me():
    email = _unique()
    r = client.post("/v1/auth/register", json={"email": email, "password": "pass12345", "name": "Ann"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["email"] == email
    assert "token" in body and body["token"]

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == email

    lg = client.post("/v1/auth/login", json={"email": email, "password": "pass12345"})
    assert lg.status_code == 200 and lg.json()["token"]

    bad = client.post("/v1/auth/login", json={"email": email, "password": "wrong-pass"})
    assert bad.status_code == 401


def test_register_validation():
    assert client.post("/v1/auth/register", json={"email": "not-an-email",
                                                  "password": "pass12345"}).status_code == 400
    assert client.post("/v1/auth/register",
                       json={"email": _unique(), "password": "short"}).status_code == 400


def test_duplicate_email_rejected():
    email = _unique()
    client.post("/v1/auth/register", json={"email": email, "password": "pass12345"})
    r = client.post("/v1/auth/register", json={"email": email, "password": "pass12345"})
    assert r.status_code == 400 and r.json()["detail"] == "email_taken"


def test_invalid_and_expired_token():
    assert client.get("/v1/auth/me", headers={"Authorization": "Bearer garbage.token.here"}).status_code == 401
    assert client.get("/v1/auth/me").status_code == 401

    orig = settings.auth_token_ttl
    try:
        settings.auth_token_ttl = -10  # 立即过期
        email = _unique()
        tok = client.post("/v1/auth/register",
                          json={"email": email, "password": "pass12345"}).json()["token"]
        assert client.get("/v1/auth/me",
                          headers={"Authorization": f"Bearer {tok}"}).status_code == 401
    finally:
        settings.auth_token_ttl = orig


def test_token_tampered_signature():
    email = _unique()
    tok = client.post("/v1/auth/register",
                      json={"email": email, "password": "pass12345"}).json()["token"]
    h, p, s = tok.split(".")
    tampered = f"{h}.{p}.{s[:-4]}aaaa"
    assert client.get("/v1/auth/me",
                      headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_social_upsert_reuses_existing_email():
    email = _unique("social")
    first = client.post("/v1/auth/register",
                        json={"email": email, "password": "pass12345"}).json()["user"]
    u = auth.upsert_social("facebook", "fb-999", email, "Social User")
    assert u["id"] == first["id"]  # 同一邮箱不重复开账号


def test_social_upsert_creates_unique_user():
    u = auth.upsert_social("x", f"x-{time.time_ns()}", "", "X User")
    assert u["provider"] == "x"
    assert u["email"].endswith("@x.local")
    assert store.get_user_by_id(u["id"]) is not None


def test_providers_endpoint_lists_email():
    body = client.get("/v1/auth/providers").json()
    assert body["providers"]["email"] is True
    assert isinstance(body["providers"]["x"], bool)
    assert isinstance(body["providers"]["facebook"], bool)


def test_logout_endpoint_ok():
    assert client.post("/v1/auth/logout").status_code == 200


def test_public_user_never_leaks_password_hash():
    email = _unique()
    client.post("/v1/auth/register", json={"email": email, "password": "pass12345"})
    u = store.get_user_by_email(email)
    assert u.get("password_hash")
    assert "password_hash" not in auth.public_user(u)
