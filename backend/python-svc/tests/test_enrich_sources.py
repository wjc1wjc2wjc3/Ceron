"""优先级 1：新增 Enrich 数据源 Provider 的单元测试。

覆盖：土地註冊 / 信貸局 / OFAC / HMT / CRS 的 mock 与降级路径，以及决策对新增信号的接入。
"""
import httpx
import pytest

from app import enrichment as E
from app.config import settings
from app.decision import assess
from app.schemas import Vertical


def _set(monkeypatch, **kw):
    for k, v in kw.items():
        monkeypatch.setattr(settings, k, v)


def test_land_search_mock_verified(monkeypatch):
    _set(monkeypatch, land_search_api_url="")
    p = E.LandRegistryProvider("", "")
    r = p.enrich("banking_mortgage", {"物业估值港币万": 1000, "物业类型": "住宅"})
    assert r["land_verified"] is True
    assert r["risk_from_enrich"] == "normal"


def test_land_search_unresolved_via_real(monkeypatch):
    _set(monkeypatch, land_search_api_url="http://x")

    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"verified": False, "charges": ["mortgage"]}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    r = E.enrich("banking_mortgage", {"物业估值港币万": 1000, "物业类型": "住宅"})
    assert r["land_unresolved"] is True
    assert r["risk_from_enrich"] == "high"
    assert any("土地" in f for f in r["flags"])


def test_land_search_degrade_on_error(monkeypatch):
    _set(monkeypatch, land_search_api_url="http://x")

    def _boom(*a, **k):
        raise httpx.ConnectError("unreachable")

    monkeypatch.setattr(httpx, "post", _boom)
    r = E.enrich("banking_mortgage", {"物业估值港币万": 1000, "物业类型": "住宅"})
    assert r["land_unresolved"] is True
    assert r["risk_from_enrich"] == "high"


def test_credit_bureau_mock_score(monkeypatch):
    _set(monkeypatch, credit_bureau_api_url="")
    p = E.CreditBureauProvider("", "")
    r = p.enrich("banking_mortgage", {"申请人": "李四"})
    assert r["credit_score"] == 720


def test_credit_bureau_adverse_via_real(monkeypatch):
    _set(monkeypatch, credit_bureau_api_url="http://x")

    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"score": 600, "adverse": True}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    r = E.enrich("banking_mortgage", {"申请人": "李四"})
    assert r["credit_adverse"] is True
    assert r["risk_from_enrich"] == "high"


def test_ofac_keyword_hit(monkeypatch):
    _set(monkeypatch, ofac_api_url="")
    p = E.OfacProvider("", "")
    r = p.enrich("family_office", {"客户姓名或实体名称": "OFAC 测试"})
    assert r["sanctions_hit"] is True
    assert any("OFAC" in f for f in r["flags"])


def test_hmt_keyword_hit(monkeypatch):
    _set(monkeypatch, hmt_api_url="")
    p = E.HmtProvider("", "")
    r = p.enrich("family_office", {"客户姓名或实体名称": "HMT 测试"})
    assert r["sanctions_hit"] is True
    assert any("HMT" in f for f in r["flags"])


def test_crs_mock_compliant(monkeypatch):
    _set(monkeypatch, crs_api_url="")
    p = E.CrsProvider("", "")
    r = p.enrich("family_office", {"客户姓名或实体名称": "张三"})
    assert r["fatca_status"] == "compliant"


def test_crs_issue_via_real(monkeypatch):
    _set(monkeypatch, crs_api_url="http://x")

    class _R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"tax_residency": "OTHER", "fatca_status": "non_compliant"}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    r = E.enrich("family_office", {"客户姓名或实体名称": "张三"})
    assert r["crs_issue"] is True
    assert r["risk_from_enrich"] == "high"


def test_decision_credit_adverse_signal():
    en = {"credit_adverse": True, "risk_from_enrich": "high"}
    d = assess(
        Vertical.banking_mortgage,
        {"贷款成数LTV": 0.5, "供款入息比率DSR": 0.4, "首期资金来源": "储蓄", "KYC状态": "完成"},
        en,
        "zh-HK",
    )
    assert d["risk_score"] >= 30
    assert any("信貸局" in r for r in d["reasons"])
