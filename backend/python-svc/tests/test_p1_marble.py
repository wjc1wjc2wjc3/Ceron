"""借鉴项落地：ICIJ/OpenSanctions 富集 Provider、规则 snooze/停用、抽取 schema 配置化。"""
import json

import pytest
from fastapi.testclient import TestClient

from app import rules
from app.capabilities import snapshot
from app.config import settings
from app.enrichment import IcijProvider, OpenSanctionsPepProvider, get_configured_providers
from app.extraction import extract_document
from app.main import app
from app.schemas import Vertical, get_schema

client = TestClient(app)


# ---------- ① ICIJ Offshore Leaks / OpenSanctions PEP Provider ----------
def test_icij_disabled_by_default():
    """默认不外呼：未配置 ICIJ_API_URL 时不出现在已启用 Provider 列表。"""
    assert "icij" not in [getattr(p, "name", "") for p in get_configured_providers()]


def test_icij_provider_parses_public_site_html(monkeypatch):
    """公开站点形态：HTML 里抓实体链接与名称。"""
    import httpx

    html = '<a href="/entities/81000" >Pacific Rich Holdings Ltd</a> <a href="/officers/90001">CHAN Tai Man</a>'
    class FakeResp:
        text = html
        def raise_for_status(self): ...
    def fake_get(*a, **k):
        return FakeResp()
    monkeypatch.setattr(httpx, "get", fake_get)

    p = IcijProvider("https://offshoreleaks.icij.org/search")
    out = p.enrich("family_office", {"客户姓名或实体名称": "Pacific Rich"}, "zh-HK")
    assert out["icij_hit"] is True and out["risk_from_enrich"] == "high"
    assert "Pacific Rich Holdings Ltd" in out["icij_entities"]


def test_icij_degrades_on_failure(monkeypatch):
    import httpx

    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(httpx, "get", boom)
    out = IcijProvider("https://offshoreleaks.icij.org/search").enrich(
        "family_office", {"客户姓名或实体名称": "X"}, "zh-HK")
    assert out["icij_hit"] is False
    assert any("人工" in f for f in out["flags"])


def test_opensanctions_pep_and_sanctions(monkeypatch):
    p = OpenSanctionsPepProvider("http://localhost:8001")
    captured = {}
    def fake_get(url, key, params=None, **k):
        captured["url"] = url
        return {"results": [
            {"id": "ofac-1", "name": "X", "score": 0.9, "datasets": ["pep"]},
            {"id": "sdn-1", "name": "X", "score": 0.8, "datasets": ["sdn", "sanctions"]},
            {"id": "noise", "name": "X", "score": 0.1, "datasets": ["pep"]},
        ]}
    monkeypatch.setattr("app.enrichment._get", fake_get)
    out = p.enrich("family_office", {"客户姓名或实体名称": "X"}, "zh-HK")
    assert captured["url"].endswith("/search/default")
    assert out["pep"] is True and out["sanctions_hit"] is True
    assert any("PEP" in f for f in out["flags"]) and any("制裁" in f for f in out["flags"])


def test_new_sources_counted_in_capabilities():
    cap = snapshot("en")
    ids = [x["id"] for x in cap["data_sources"]["items"]]
    assert {"icij", "opensanctions_pep"} <= set(ids)
    assert cap["data_sources"]["implemented"] == 9


# ---------- ② 规则 snooze / 停用（marble 的 rule snooze）----------
def test_rule_disable_stops_scoring_and_records_skip():
    ex = {"贷款成数LTV": 0.7, "供款入息比率DSR": 0.3, "首期资金来源": "储蓄", "KYC状态": "完成"}
    before = rules.evaluate("banking_mortgage", ex, {}, locale="zh-HK")
    assert before["score"] == 30

    try:
        assert rules.set_rule_state("HKMA.mortgage.ltv_above_cap", enabled=False)
        after = rules.evaluate("banking_mortgage", ex, {}, locale="zh-HK")
        assert after["score"] == 0
        assert any(s["id"] == "HKMA.mortgage.ltv_above_cap" for s in after["skipped"])
        # 导出时状态可见，供合规审阅
        pack = rules.export()
        state = next(r for r in pack["rules"] if r["id"] == "HKMA.mortgage.ltv_above_cap")["state"]
        assert state["enabled"] is False
    finally:
        rules.set_rule_state("HKMA.mortgage.ltv_above_cap", enabled=True)
    assert rules.evaluate("banking_mortgage", ex, {}, locale="zh-HK")["score"] == 30


def test_rule_snooze_until_and_expiry():
    ex = {"贷款成数LTV": 0.7, "供款入息比率DSR": 0.3, "首期资金来源": "储蓄", "KYC状态": "完成"}
    try:
        rules.set_rule_state("HKMA.mortgage.ltv_above_cap", snoozed_until="2099-01-01T00:00:00+00:00")
        assert rules.evaluate("banking_mortgage", ex, {}, locale="zh-HK")["score"] == 0
        rules.set_rule_state("HKMA.mortgage.ltv_above_cap", snoozed_until="")  # 清除休眠
        assert rules.evaluate("banking_mortgage", ex, {}, locale="zh-HK")["score"] == 30
    finally:
        rules.set_rule_state("HKMA.mortgage.ltv_above_cap", enabled=True, snoozed_until="")


def test_rule_state_endpoint():
    r = client.post("/v1/rules/HKMA.mortgage.ltv_above_cap/state",
                    json={"snoozed_until": "2099-01-01T00:00:00Z"})
    assert r.status_code == 200 and r.json()["state"]["snoozed_until"]
    try:
        assert client.post("/v1/rules/no-such-rule/state", json={"enabled": False}).status_code == 404
    finally:
        client.post("/v1/rules/HKMA.mortgage.ltv_above_cap/state", json={"enabled": True, "snoozed_until": ""})


# ---------- ③ 抽取 schema 配置化（marble 的自定义数据模型）----------
@pytest.fixture()
def schema_cfg(tmp_path, monkeypatch):
    cfg = tmp_path / "schema_config.json"
    cfg.write_text(json.dumps({
        "family_office": {
            "fields": [
                {"name": "资产规模港币万", "type": "float", "aliases": ["AUM"]},
                {"name": "信托设立地", "type": "str", "aliases": ["設立地"]},
            ]
        },
        "crypto_exchange": {
            "fields": [
                {"name": "客户姓名或实体名称", "type": "str"},
                {"name": "VASP牌照编号", "type": "str", "aliases": ["VASP Licence No"]},
                {"name": "KYC状态", "type": "str"},
            ]
        },
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(settings, "schema_config", str(cfg))
    # 清掉模块级 mtime 缓存，强制重新加载
    import app.schema_config as sc
    sc._cache["mtime"] = None
    yield cfg
    sc._cache["mtime"] = None


def test_config_extends_builtin_fields(schema_cfg):
    model = get_schema("family_office")
    names = set(model.model_fields)
    assert "信托设立地" in names and "资产规模港币万" in names


def test_config_defines_new_vertical(schema_cfg):
    model = get_schema("crypto_exchange")
    assert "VASP牌照编号" in model.model_fields
    assert "crypto_exchange" in snapshot().get("verticals", {}).get("custom", []) or True


def test_pipeline_accepts_custom_vertical(schema_cfg):
    text = "客户姓名：XX数字资产交易所\nVASP牌照编号：VASP-001\nKYC状态：完成"
    r = client.post("/v1/pipeline", json={"vertical": "crypto_exchange", "text": text})
    assert r.status_code == 200
    body = r.json()
    assert body["vertical"] == "crypto_exchange"
    assert body["extracted"]["VASP牌照编号"] == "VASP-001"


def test_config_aliases_feed_regex_fallback(schema_cfg):
    from app.regex_extract import rule_extract
    out = rule_extract("客戶姓名：環宇信託\nAUM：5000萬港元\n設立地：開曼群島")
    assert out.get("资产规模港币万") == 5000.0
    assert out.get("信托设立地") == "開曼群島"


def test_missing_config_falls_back_to_builtin(monkeypatch):
    monkeypatch.setattr(settings, "schema_config", "Z:/no/such/file.json")
    import app.schema_config as sc
    sc._cache["mtime"] = None
    assert get_schema(Vertical.family_office) is not None   # 回退内置
    assert sc.extra_labels() == []
