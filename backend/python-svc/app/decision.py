"""决策服务（Decisioning）：风险评分 + 合規閘口，输出审批建议。

对应 Heron 的 decisioning：按客戶政策跑檢查，輸出通过/拒绝/转人工及理由。
"""
from typing import Any

from app.schemas import Vertical


def assess(vertical: Vertical, extracted: dict, enrichment: dict | None = None) -> dict:
    enrichment = enrichment or {}
    fields = list(extracted.keys())
    filled = sum(1 for v in extracted.values() if v not in (None, "", []))
    completeness = round(filled / max(len(fields), 1), 2) if fields else 0.0

    risk_score = 0
    reasons: list[str] = []

    if completeness < 0.5:
        risk_score += 40
        reasons.append(f"资料完整度偏低（{completeness}），需补充材料。")

    if vertical == Vertical.insurance_hk:
        if extracted.get("资料完整度") is not None and extracted["资料完整度"] < 0.8:
            risk_score += 20
            reasons.append("理赔资料不完整，存在核查必要。")
        claim = extracted.get("理赔金额港币万") or 0
        insured = extracted.get("保额港币万") or 0
        if insured and claim and claim / insured > 0.8:
            risk_score += 25
            reasons.append("理赔金额接近保额，残值/道德风险偏高。")

    elif vertical == Vertical.family_office:
        if not extracted.get("资金来源"):
            risk_score += 20
            reasons.append("缺少资金来源说明，CDD 不完整。")
        if extracted.get("KYC状态") in ("待补", "未完成"):
            risk_score += 15
            reasons.append("KYC 未完成。")

    # 來自富集服務的高風險信號
    if enrichment.get("sanctions_hit"):
        risk_score += 60
        reasons.append("制裁名單命中，直接拒絕並上報。")
    if enrichment.get("pep"):
        risk_score += 20
        reasons.append("PEP：需加强尽调。")

    if not reasons:
        reasons.append("关键字段齐全，风险信号可控。")

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
