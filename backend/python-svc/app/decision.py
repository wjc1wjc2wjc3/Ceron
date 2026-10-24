"""决策服务（Decisioning）：风险评分 + 合規閘口，输出审批建议。

决策引擎：按客户政策跑检查，输出通过/拒绝/转人工及理由。
"""
from typing import Any

from app.schemas import Vertical


def tr(locale: str, hk: str, en: str, cn: str) -> str:
    """按 locale 返回对应语文的决策/富集文案。"""
    return {"zh-HK": hk, "en": en, "zh-CN": cn}.get(locale, hk)


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
