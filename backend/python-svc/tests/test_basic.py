"""基础测试：脱敏、正则兜底、抽取+富集+决策流水线。"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.compliance import mask_pii, check_data_residency  # noqa: E402
from app.regex_extract import rule_extract  # noqa: E402
from app.schemas import Vertical  # noqa: E402
from app.extraction import extract_document  # noqa: E402
from app.enrichment import enrich  # noqa: E402
from app.decision import assess  # noqa: E402


def test_mask_pii():
    txt = "身份证 110101199003071234 手机 13800138000 港电话 +85291234567"
    masked = mask_pii(txt)
    assert "****" in masked
    assert "110101199003071234" not in masked
    assert "+85291234567" not in masked or "****" in masked


def test_rule_extract():
    raw = "投保人：香港環宇保險有限公司\n保單號：HK12345\n保額：800萬\n理賠金額：120萬"
    data = rule_extract(raw)
    assert data["投保人"] == "香港環宇保險有限公司"
    assert data["保单号"] == "HK12345"
    assert "_金额候选" in data


def test_data_residency():
    assert check_data_residency()["compliant"] is True


def test_pipeline():
    asyncio.run(_run())


async def _run():
    text = (
        "投保人：香港環宇保險有限公司\n保單號：HK12345\n受保人：張三\n"
        "險種：終身壽險\n保額：800萬\n年繳保費：20萬\n理賠類型：身故\n理賠金額：120萬\n資料完整度：0.9"
    )
    res = await extract_document(text, Vertical.insurance_hk)
    assert res["vertical"] == "insurance_hk"

    enrichment = enrich(res["vertical"], res["extracted"])
    decision = assess(Vertical.insurance_hk, res["extracted"], enrichment)
    assert decision["action"] in ("approve", "manual_review", "reject")
