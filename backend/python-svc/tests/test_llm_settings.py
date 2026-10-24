"""用户自主选择/自定义大模型：目录、保存、脱敏、自定义模型、连通性测试。"""
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app import llm, llm_catalog, store
from app.main import app

client = TestClient(app)


def _register():
    email = f"llm-{time.time_ns()}@example.hk"
    r = client.post("/v1/auth/register",
                    json={"email": email, "password": "pass12345", "name": "LLM User"})
    return r.json()["token"], r.json()["user"]["id"]


def test_presets_include_all_five_vendors():
    ids = {p["id"] for p in client.get("/v1/llm/presets").json()["presets"]}
    assert {"deepseek", "kimi", "glm", "qwen", "doubao"} <= ids


def test_settings_requires_auth():
    assert client.get("/v1/llm/settings").status_code == 401
    assert client.put("/v1/llm/settings", json={"active": "deepseek"}).status_code == 401


def test_select_builtin_and_key_is_masked():
    token, uid = _register()
    h = {"Authorization": f"Bearer {token}"}
    r = client.put("/v1/llm/settings", json={
        "active": "deepseek",
        "providers": {"deepseek": {"api_key": "sk-secret-key-1234", "model": "deepseek-chat"}},
    }, headers=h)
    assert r.status_code == 200
    got = client.get("/v1/llm/settings", headers=h).json()["settings"]
    assert got["active"] == "deepseek"
    assert got["providers"]["deepseek"]["has_key"] is True

    masked = got["providers"]["deepseek"]["api_key_masked"]
    assert "sk-secret-key-1234" not in masked and masked
    assert "1234" in masked  # 仅保留前后各 4 位
    # 服务端保留完整密钥
    assert store.get_llm_config(uid)["providers"]["deepseek"]["api_key"] == "sk-secret-key-1234"


def test_masked_key_roundtrip_preserves_secret():
    token, uid = _register()
    h = {"Authorization": f"Bearer {token}"}
    client.put("/v1/llm/settings", json={
        "active": "qwen",
        "providers": {"qwen": {"api_key": "sk-qwen-abcdef"}},
    }, headers=h)
    masked = client.get("/v1/llm/settings", headers=h).json()["settings"]["providers"]["qwen"]["api_key_masked"]
    # 前端原样回传脱敏值（不应覆盖/清空真实密钥）
    client.put("/v1/llm/settings", json={
        "active": "qwen",
        "providers": {"qwen": {"api_key": masked, "model": "qwen-max"}},
    }, headers=h)
    cfg = store.get_llm_config(uid)
    assert cfg["providers"]["qwen"]["api_key"] == "sk-qwen-abcdef"
    assert cfg["providers"]["qwen"]["model"] == "qwen-max"


def test_add_and_delete_custom_model():
    token, _ = _register()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/v1/llm/custom", json={
        "name": "内部 Llama", "model": "llama-3-70b",
        "base_url": "https://llm.internal/v1/", "api_key": "k-12345678",
    }, headers=h)
    assert r.status_code == 200
    cid = r.json()["custom"]["id"]
    assert r.json()["custom"]["api_key_masked"] != "k-12345678"

    got = client.get("/v1/llm/settings", headers=h).json()["settings"]
    assert any(c["id"] == cid for c in got["customs"])
    assert got["active"] == cid  # 首个自定义模型自动启用

    assert client.delete(f"/v1/llm/custom/{cid}", headers=h).json()["ok"] is True
    assert client.get("/v1/llm/settings", headers=h).json()["settings"]["customs"] == []


def test_custom_model_requires_base_url_and_model():
    token, _ = _register()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/v1/llm/custom", json={"name": "x", "model": "", "base_url": ""}, headers=h)
    assert r.status_code == 400 and r.json()["detail"] == "base_url_and_model_required"


def test_unknown_provider_rejected():
    token, _ = _register()
    h = {"Authorization": f"Bearer {token}"}
    r = client.put("/v1/llm/settings", json={"active": "not-a-vendor"}, headers=h)
    assert r.status_code == 400 and r.json()["detail"] == "unknown_provider"


def test_resolve_uses_custom_endpoint_and_model():
    cfg = llm_catalog.resolve({
        "active": "cm-1",
        "customs": [{"id": "cm-1", "name": "mine", "model": "my-model",
                     "base_url": "https://my.llm/v1", "api_key": "k"}],
    })
    assert cfg.provider == "custom" and cfg.model == "my-model"
    assert cfg.base_url == "https://my.llm/v1" and cfg.usable() is True


def test_resolve_falls_back_to_service_env_when_unset():
    cfg = llm_catalog.resolve(None)
    assert cfg.provider == "mock"  # 未配置时零成本运行
    assert cfg.usable() is False


def test_connection_test_success_and_failure(monkeypatch):
    token, _ = _register()
    h = {"Authorization": f"Bearer {token}"}

    class _Ok:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}]}

    class _Fail:
        status_code = 401

        def raise_for_status(self):
            raise httpx.HTTPStatusError("401", request=None, response=_Fail())

        def json(self):
            return {"error": {"message": "invalid key"}}

    def _client_factory(*a, **k):
        class _C:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *args):
                return False

            async def post(self_inner, *args, **kwargs):
                return _Ok()
        return _C()

    monkeypatch.setattr(httpx, "AsyncClient", _client_factory)
    ok = client.post("/v1/llm/test", json={
        "provider": "deepseek", "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat", "api_key": "sk-test",
    }, headers=h).json()
    assert ok["ok"] is True and ok["model"] == "deepseek-chat"

    def _fail_factory(*a, **k):
        class _C:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *args):
                return False

            async def post(self_inner, *args, **kwargs):
                raise httpx.HTTPStatusError("401", request=None, response=_Fail())
        return _C()

    monkeypatch.setattr(httpx, "AsyncClient", _fail_factory)
    bad = client.post("/v1/llm/test", json={
        "provider": "deepseek", "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat", "api_key": "wrong",
    }, headers=h).json()
    assert bad["ok"] is False


def test_connection_test_without_credentials():
    token, _ = _register()
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/v1/llm/test", json={"provider": "deepseek", "api_key": ""}, headers=h).json()
    assert r["ok"] is False and r["error"] == "missing_base_url_model_or_key"


def test_pipeline_uses_user_selected_model(monkeypatch):
    """已登录且选定模型时，抽取请求应打到用户配置的 base_url。"""
    token, uid = _register()
    h = {"Authorization": f"Bearer {token}"}
    client.post("/v1/llm/custom", json={
        "name": "spy", "model": "spy-model",
        "base_url": "https://spy.llm/v1", "api_key": "k-12345678",
    }, headers=h)

    seen = {}

    def _spy_factory(*a, **k):
        class _C:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *args):
                return False

            async def post(self_inner, url, **kwargs):
                seen["url"] = url
                seen["payload"] = kwargs.get("json", {})

                class _R:
                    status_code = 200

                    def raise_for_status(self_inner):
                        pass

                    def json(self_inner):
                        return {"choices": [{"message": {"content": "{}"}}]}
                return _R()
        return _C()

    monkeypatch.setattr(httpx, "AsyncClient", _spy_factory)
    client.post("/v1/pipeline", json={"vertical": "insurance_hk", "text": "投保单 保单号 HK1"}, headers=h)
    assert seen["url"].startswith("https://spy.llm/v1")
    assert seen["payload"]["model"] == "spy-model"


def test_custom_model_can_disable_json_mode(monkeypatch):
    """不支持 response_format 的模型：json_mode=false 时请求体不应带该字段。"""
    token, _ = _register()
    h = {"Authorization": f"Bearer {token}"}
    client.post("/v1/llm/custom", json={
        "name": "nojson", "model": "m1", "base_url": "https://x.llm/v1",
        "api_key": "k-12345678", "json_mode": False,
    }, headers=h)

    seen = {}

    def _spy_factory(*a, **k):
        class _C:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *args):
                return False

            async def post(self_inner, url, **kwargs):
                seen["payload"] = kwargs.get("json", {})

                class _R:
                    status_code = 200

                    def raise_for_status(self_inner):
                        pass

                    def json(self_inner):
                        return {"choices": [{"message": {"content": "{}"}}]}
                return _R()
        return _C()

    monkeypatch.setattr(httpx, "AsyncClient", _spy_factory)
    client.post("/v1/pipeline", json={"vertical": "insurance_hk", "text": "投保单"}, headers=h)
    assert "response_format" not in seen["payload"]
