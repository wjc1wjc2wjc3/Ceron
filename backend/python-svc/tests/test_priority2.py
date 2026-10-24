"""优先级 2：四条新业务线的合规闸口与决策规则。"""
from app.decision import assess
from app.schemas import Vertical


def test_banking_mortgage_ltv_dsr():
    ex = {"贷款成数LTV": 0.7, "供款入息比率DSR": 0.62, "首期资金来源": "储蓄", "KYC状态": "完成"}
    d = assess(Vertical.banking_mortgage, ex, {}, "zh-HK")
    assert d["action"] in ("manual_review", "reject")
    joined = " ".join(d["reasons"])
    assert "LTV" in joined and "DSR" in joined


def test_banking_mortgage_clean_approve():
    ex = {"贷款成数LTV": 0.5, "供款入息比率DSR": 0.4, "首期资金来源": "储蓄", "KYC状态": "完成"}
    d = assess(Vertical.banking_mortgage, ex, {}, "en")
    assert d["action"] == "approve"


def test_securities_suitability_mismatch():
    ex = {"风险承受度": "低", "产品风险等级": "高", "投资经验年": 1, "KYC状态": "完成"}
    d = assess(Vertical.securities_suitability, ex, {}, "zh-HK")
    assert d["risk_score"] >= 35
    assert any("承受度" in r for r in d["reasons"])


def test_mpf_employer_unregistered():
    ex = {"雇主登记状态": "未登记", "雇员状态": "在职", "供款状态": "正常", "KYC状态": "完成"}
    d = assess(Vertical.mpf, ex, {}, "zh-HK")
    assert d["risk_score"] >= 30
    assert any("未登記" in r for r in d["reasons"])


def test_fund_retail_unauthorized():
    ex = {
        "是否获证监会认可": "否",
        "投资者类型": "零售",
        "结构类型": "OFC",
        "管理公司": "X",
        "受益所有人": "Y",
        "KYC状态": "完成",
    }
    d = assess(Vertical.fund_ofc_lpf, ex, {}, "zh-HK")
    assert d["risk_score"] >= 40
    assert any("零售" in r for r in d["reasons"])
