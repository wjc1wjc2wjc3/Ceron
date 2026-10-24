"""扩展测试：OCR、富集 Provider、family_office 垂直、英文/繁中抽取。"""
import asyncio
import base64
import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ocr import get_ocr_provider  # noqa: E402
from app.enrichment import get_enrich_provider, enrich  # noqa: E402
from app.regex_extract import rule_extract  # noqa: E402
from app.schemas import Vertical  # noqa: E402
from app.extraction import extract_document  # noqa: E402
from app.decision import assess  # noqa: E402
from app.config import settings  # noqa: E402


def test_ocr_mock_returns_text():
    provider = get_ocr_provider()
    assert provider.name == "mock"
    text = "保單號：HK12345 保額：800萬"
    encoded = base64.b64encode(text.encode("utf-8")).decode()
    out = asyncio.run(provider.recognize(encoded))
    assert "HK12345" in out


def test_enrich_provider_default_mock():
    provider = get_enrich_provider()
    assert provider.name == "mock"
    result = enrich("insurance_hk", {"投保人": "香港環宇保險有限公司", "保单号": "HK12345"})
    assert result["provider"] == "mock"
    assert result["icris_verified"] is True


def test_enrich_pep_flag():
    result = enrich("family_office", {"客户姓名或实体名称": "測試人物", "是否政治公众人物PEP": True})
    assert result["pep"] is True
    assert result["risk_from_enrich"] == "high"


def test_regex_english_money_prefix():
    raw = "Policy No: HK9876543\nInsured: Chan Tai Man\nSum Insured: HKD 8,000,000\nClaim Amount: HKD 1,200,000"
    data = rule_extract(raw)
    assert data["保单号"] == "HK9876543"
    # "Sum Insured" 不应误抽为受保人
    assert data.get("受保人") == "Chan Tai Man"
    assert 800.0 in data["_金额候选"]
    assert 120.0 in data["_金额候选"]


def test_family_office_pipeline():
    text = (
        "客戶姓名：陳大文家族辦公室有限公司\n身份類型：公司\n"
        "資產規模：50,000萬港元\n資金來源：家族持股出售所得\n受益所有人：陳大文\nKYC狀態：待補"
    )

    async def run():
        res = await extract_document(text, Vertical.family_office)
        enrichment = enrich(res["vertical"], res["extracted"])
        decision = assess(Vertical.family_office, res["extracted"], enrichment)
        return res, enrichment, decision

    res, enrichment, decision = asyncio.run(run())
    assert res["extracted"].get("资产规模港币万") == 50000.0
    assert decision["action"] in ("approve", "manual_review", "reject")


def test_enrich_runs_icris_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "icris_api_url", "http://fake-icris")
    monkeypatch.setattr(settings, "icris_api_key", "k")
    monkeypatch.setattr(settings, "sanctions_api_url", "")
    with patch("httpx.post") as m:
        m.return_value = Mock(status_code=200, json=lambda: {"verified": True, "company_status": "Active"})
        result = enrich("insurance_hk", {"投保人": "X有限公司", "保单号": "HK1"})
        assert result["provider"] == "icris"
        assert result["icris_verified"] is True
        assert result["icris_company_status"] == "Active"
        m.assert_called_once()
        _, kwargs = m.call_args
        assert kwargs["json"]["company_name"] == "X有限公司"
        assert kwargs["headers"]["Authorization"] == "Bearer k"


def test_enrich_icris_degrades_on_error(monkeypatch):
    monkeypatch.setattr(settings, "icris_api_url", "http://fake-icris")
    monkeypatch.setattr(settings, "icris_api_key", "")
    monkeypatch.setattr(settings, "sanctions_api_url", "")
    with patch("httpx.post", side_effect=Exception("boom")):
        result = enrich("insurance_hk", {"投保人": "X有限公司"})
        assert result["provider"] == "icris"
        assert any("人工複核" in f for f in result["flags"])
        assert result["risk_from_enrich"] == "high"


def test_enrich_runs_both_providers(monkeypatch):
    monkeypatch.setattr(settings, "icris_api_url", "http://fake-icris")
    monkeypatch.setattr(settings, "sanctions_api_url", "http://fake-sanctions")
    with patch("httpx.post") as m:
        m.return_value = Mock(
            status_code=200,
            json=lambda: {"verified": True, "company_status": "Active"}
            if m.call_count == 1 else {"hit": True, "lists": ["UN"]},
        )
        result = enrich("family_office", {"客户姓名或实体名称": "陳大文家族辦公室", "受益所有人": "陳大文"})
        assert result["provider"] == "icris+sanctions"
        assert result["icris_verified"] is True
        assert result["sanctions_hit"] is True
        assert any("制裁名單命中" in f for f in result["flags"])
