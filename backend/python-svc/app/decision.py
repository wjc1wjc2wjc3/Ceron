"""决策服务（Decisioning）：风险评分 + 合規閘口，输出审批建议。

决策引擎：按客户政策跑检查，输出通过/拒绝/转人工及理由。
"""
from typing import Any

from app.schemas import Vertical


def tr(locale: str, hk: str, en: str, cn: str) -> str:
    """按 locale 返回对应语文的决策/富集文案。"""
    return {"zh-HK": hk, "en": en, "zh-CN": cn}.get(locale, hk)


# 风险等级有序映射，用于证券合适性等「承受度 vs 产品风险」比较。
_RISK_ORDER = {"低": 1, "中": 2, "高": 3}


def _risk_level(v: object) -> int:
    if isinstance(v, str) and v in _RISK_ORDER:
        return _RISK_ORDER[v]
    return 0


def assess(
    vertical: Vertical,
    extracted: dict,
    enrichment: dict | None = None,
    locale: str = "zh-HK",
) -> dict:
    enrichment = enrichment or {}
    fields = list(extracted.keys())
    filled = sum(1 for v in extracted.values() if v not in (None, "", []))
    completeness = round(filled / max(len(fields), 1), 2) if fields else 0.0

    risk_score = 0
    reasons: list[str] = []

    if completeness < 0.5:
        risk_score += 40
        reasons.append(
            tr(locale,
               f"資料完整度偏低（{completeness}），需補充材料。",
               f"Low data completeness ({completeness}); additional documents required.",
               f"资料完整度偏低（{completeness}），需补充材料。")
        )

    if vertical == Vertical.insurance_hk:
        if extracted.get("资料完整度") is not None and extracted["资料完整度"] < 0.8:
            risk_score += 20
            reasons.append(
                tr(locale,
                   "理賠資料不完整，存在核查必要。",
                   "Incomplete claim documents; verification required.",
                   "理赔资料不完整，存在核查必要。")
            )
        claim = extracted.get("理赔金额港币万") or 0
        insured = extracted.get("保额港币万") or 0
        if insured and claim and claim / insured > 0.8:
            risk_score += 25
            reasons.append(
                tr(locale,
                   "理賠金額接近保額，殘值/道德風險偏高。",
                   "Claim amount is close to sum assured; elevated moral-hazard risk.",
                   "理赔金额接近保额，残值/道德风险偏高。")
            )

    elif vertical == Vertical.family_office:
        if not extracted.get("资金来源"):
            risk_score += 20
            reasons.append(
                tr(locale,
                   "缺少資金來源說明，CDD 不完整。",
                   "Missing source-of-funds explanation; CDD incomplete.",
                   "缺少资金来源说明，CDD 不完整。")
            )
        if extracted.get("KYC状态") in ("待补", "未完成"):
            risk_score += 15
            reasons.append(
                tr(locale,
                   "KYC 未完成。",
                   "KYC not completed.",
                   "KYC 未完成。")
            )

    elif vertical == Vertical.banking_mortgage:
        ltv = extracted.get("贷款成数LTV")
        if ltv is not None and ltv > 0.6:
            risk_score += 30
            reasons.append(
                tr(locale,
                   "按揭成數(LTV)超 HKMA 上限 60%，需按揭保險或加壓力測試。",
                   "Loan-to-value (LTV) exceeds the HKMA 60% cap; mortgage insurance or stress test required.",
                   "按揭成数(LTV)超 HKMA 上限 60%，需按揭保险或加压力测试。")
            )
        dsr = extracted.get("供款入息比率DSR")
        if dsr is not None and dsr > 0.5:
            risk_score += 25
            reasons.append(
                tr(locale,
                   "供款入息比率(DSR)超 50%，還款能力存疑。",
                   "Debt-servicing ratio (DSR) exceeds 50%; repayment capacity questionable.",
                   "供款入息比率(DSR)超 50%，还款能力存疑。")
            )
        if not extracted.get("首期资金来源"):
            risk_score += 15
            reasons.append(
                tr(locale,
                   "缺少首期資金來源說明，CDD 不完整。",
                   "Missing source-of-down-payment explanation; CDD incomplete.",
                   "缺少首期资金来源说明，CDD 不完整。")
            )

    elif vertical == Vertical.securities_suitability:
        client_lv = _risk_level(extracted.get("风险承受度"))
        product_lv = _risk_level(extracted.get("产品风险等级"))
        if client_lv and product_lv and product_lv > client_lv:
            risk_score += 35
            reasons.append(
                tr(locale,
                   "產品風險超出客戶風險承受度，存在不適合性 / 誤售風險。",
                   "Product risk exceeds client's risk tolerance; unsuitability / mis-selling risk.",
                   "产品风险超出客户风险承受度，存在不适合性 / 误售风险。")
            )
        if product_lv == 3 and extracted.get("投资经验年") is not None and extracted["投资经验年"] < 2:
            risk_score += 20
            reasons.append(
                tr(locale,
                   "高風險產品但投資經驗不足，需加強風險揭示。",
                   "High-risk product but insufficient investment experience; enhance risk disclosure.",
                   "高风险产品但投资经验不足，需加强风险揭示。")
            )

    elif vertical == Vertical.mpf:
        if extracted.get("雇主登记状态") == "未登记":
            risk_score += 30
            reasons.append(
                tr(locale,
                   "僱主未登記強積金計劃，違反 MPFA 合規。",
                   "Employer not registered for MPF scheme; MPFA non-compliance.",
                   "雇主未登记强积金计划，违反 MPFA 合规。")
            )
        if extracted.get("雇员状态") not in (None, "", "在职", "自雇"):
            risk_score += 20
            reasons.append(
                tr(locale,
                   "僱員狀態不符供款資格。",
                   "Employee status does not meet contribution eligibility.",
                   "雇员状态不符供款资格。")
            )
        if extracted.get("供款状态") == "逾期":
            risk_score += 15
            reasons.append(
                tr(locale,
                   "供款逾期，需跟進。",
                   "Contributions overdue; follow-up required.",
                   "供款逾期，需跟进。")
            )

    elif vertical == Vertical.fund_ofc_lpf:
        if extracted.get("是否获证监会认可") == "否" and extracted.get("投资者类型") == "零售":
            risk_score += 40
            reasons.append(
                tr(locale,
                   "未獲證監會認可卻面向零售投資者，違規。",
                   "Not SFC-authorized yet offered to retail investors; non-compliant.",
                   "未获证监会认可却面向零售投资者，违规。")
            )
        if not extracted.get("受益所有人"):
            risk_score += 20
            reasons.append(
                tr(locale,
                   "缺少受益所有人，CDD 不完整。",
                   "Missing beneficial owner; CDD incomplete.",
                   "缺少受益所有人，CDD 不完整。")
            )
        if extracted.get("结构类型") in ("OFC", "LPF", "REIT") and not extracted.get("管理公司"):
            risk_score += 15
            reasons.append(
                tr(locale,
                   "基金結構已聲明但管理公司缺失，需補正。",
                   "Fund structure stated but manager missing; needs completion.",
                   "基金结构已声明但管理公司缺失，需补正。")
            )

    # 來自富集服務的高風險信號
    if enrichment.get("sanctions_hit"):
        risk_score += 60
        reasons.append(
            tr(locale,
               "制裁名單命中，直接拒絕並上報。",
               "Sanctions list hit: auto-reject and report.",
               "制裁名单命中，直接拒绝并上报。")
        )
    if enrichment.get("pep"):
        risk_score += 20
        reasons.append(
            tr(locale,
               "PEP：需加強盡調。",
               "PEP: enhanced due diligence required.",
               "PEP：需加强尽调。")
        )

    if not reasons:
        reasons.append(
            tr(locale,
               "關鍵欄位齊全，風險信號可控。",
               "Key fields complete; risk signals under control.",
               "关键字段齐全，风险信号可控。")
        )

    if risk_score >= 60:
        action = "reject"
    elif risk_score >= 25:
        action = "manual_review"
    else:
        action = "approve"

    return {
        "completeness": completeness,
        "risk_score": risk_score,
        "action": action,
        "reasons": reasons,
    }
