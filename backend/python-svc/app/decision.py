"""决策服务（Decisioning）：风险评分 + 合規閘口，输出审批建议。

判断条件已从硬编码 if/elif 迁移到 ``app/rules.py`` 的**可版本化规则包**：
- 每条命中都留痕（``rules_hit``），可被审计包导出；
- 决策结果带 ``rule_pack`` 版本，换模型不影响审计口径；
- 风险不再是单一分数线，而是带位（low/medium/high/critical）+ 处置动作。
"""
from typing import Any

from app import rules
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

    vkey = vertical.value if isinstance(vertical, Vertical) else str(vertical)
    run = rules.evaluate(vkey, extracted, enrichment, locale=locale, completeness=completeness)
    risk_score = run["score"]
    reasons = list(run["reasons"])
    hits = run["hits"]

    if not reasons:
        reasons.append(
            tr(locale,
               "關鍵欄位齊全，風險信號可控。",
               "Key fields complete; risk signals under control.",
               "关键字段齐全，风险信号可控。")
        )

    band, action = rules.band_of(risk_score)

    return {
        "action": action,
        "risk_score": risk_score,
        "reasons": reasons,
        # --- 新增：结构化可审计信息 ---
        "risk_level": band,                       # low / medium / high / critical
        "risk_band": band,                        # 兼容 kyc-analyst 风格命名
        "completeness": completeness,
        "rule_pack": {
            "version": rules.RULE_PACK_VERSION,
            "count": len(rules.RULES),
        },
        "rules_hit": hits,
        "gates": sorted({h["gate"] for h in hits}),
        "severity": max(
            [h["severity"] for h in hits],
            key=lambda s: {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(s, 0),
            default="none",
        ),
        "evidence": [
            {"rule": h["id"], "gate": h["gate"], "fields": h["fields"], "reason": h["reason"]}
            for h in hits
        ],
    }


def assess_with_review(
    vertical: Vertical,
    extracted: dict,
    enrichment: dict | None = None,
    locale: str = "zh-HK",
    trace: list | None = None,
) -> dict:
    """决策 + 人工复核分级（HITL 检查点），供 /v1/pipeline 使用。"""
    from app.review import build_review

    enrichment = dict(enrichment or {})
    decision = assess(vertical, extracted, enrichment, locale)
    # 供 review 与规则使用的完整度上下文
    fields = list(extracted.keys())
    filled = sum(1 for v in extracted.values() if v not in (None, "", []))
    enrichment["_completeness"] = round(filled / max(len(fields), 1), 2) if fields else 0.0
    decision["review"] = build_review(
        vertical.value if isinstance(vertical, Vertical) else str(vertical),
        extracted, enrichment, decision, trace, locale,
    )
    return decision
