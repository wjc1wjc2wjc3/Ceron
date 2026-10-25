"""人工覆核分級（HITL）：把單一的「需人工覆核」標記細化為**多級檢查點**。

借鑒 kyc-analyst 的 17 個 stagegate（每個代理行為前都需人類顯式確認）與 Marble 的
Case Manager：把「什麼情況下必須喊人」列成可枚舉、可審計、可解釋的檢查點，
而不是一個黑盒的 boolean。

級別由輕到重：none < field < source < gate < risk
  - field  ：字段缺失 / 填寫不清（補件即可）
  - source ：數據源降級或不可用（需人工自行取證）
  - gate   ：命中監管閘口（需合規同事判斷）
  - risk   ：風險分帶位達到高/critical（需簽批）
"""
from typing import Any

LEVEL_ORDER = {"none": 0, "field": 1, "source": 2, "gate": 3, "risk": 4}

_LABEL = {
    "field": {"zh-HK": "字段缺失：需補件", "en": "Missing fields: request documents", "zh-CN": "字段缺失：需补件"},
    "source": {"zh-HK": "數據源降級：需人工取證", "en": "Data source degraded: manual evidence", "zh-CN": "数据源降级：需人工取证"},
    "gate": {"zh-HK": "監管閘口命中：需合規判斷", "en": "Compliance gate hit: compliance decision", "zh-CN": "监管闸口命中：需合规判断"},
    "risk": {"zh-HK": "風險帶位偏高：需簽批", "en": "Elevated risk band: sign-off required", "zh-CN": "风险带位偏高：需签批"},
}

_TXT = {
    "CP-01": {
        "zh-HK": "必填字段缺失：{fields}",
        "en": "Required fields missing: {fields}",
        "zh-CN": "必填字段缺失：{fields}",
    },
    "CP-02": {
        "zh-HK": "資料完整度偏低（{completeness}）",
        "en": "Low data completeness ({completeness})",
        "zh-CN": "资料完整度偏低（{completeness}）",
    },
    "CP-03": {
        "zh-HK": "受益所有人(UBO)未識別",
        "en": "Beneficial owner (UBO) not resolved",
        "zh-CN": "受益所有人(UBO)未识别",
    },
    "CP-04": {
        "zh-HK": "資金來源說明缺失",
        "en": "Source-of-funds explanation missing",
        "zh-CN": "资金来源说明缺失",
    },
    "CP-05": {
        "zh-HK": "富集數據源降級：{providers}",
        "en": "Enrichment source degraded: {providers}",
        "zh-CN": "富集数据源降级：{providers}",
    },
    "CP-06": {
        "zh-HK": "制裁名單命中，需合規確認",
        "en": "Sanctions hit: compliance confirmation required",
        "zh-CN": "制裁名单命中，需合规确认",
    },
    "CP-07": {
        "zh-HK": "PEP 命中，需加強盡調",
        "en": "PEP hit: enhanced due diligence required",
        "zh-CN": "PEP 命中，需加强尽调",
    },
    "CP-08": {
        "zh-HK": "風險帶位為 {band}，需簽批",
        "en": "Risk band {band}: sign-off required",
        "zh-CN": "风险带位为 {band}，需签批",
    },
    "CP-09": {
        "zh-HK": "命中 critical 級規則：{rules}",
        "en": "Critical rule(s) hit: {rules}",
        "zh-CN": "命中 critical 级规则：{rules}",
    },
    "CP-10": {
        "zh-HK": "抽取走的是規則/模擬兜底，字段準確率待核",
        "en": "Extraction used rule/mock fallback; field accuracy needs check",
        "zh-CN": "抽取走的是规则/模拟兜底，字段准确率待核",
    },
}


def _msg(cp_id: str, locale: str, **vars: Any) -> str:
    tpl = (_TXT.get(cp_id) or {}).get(locale) or (_TXT.get(cp_id) or {}).get("zh-HK") or cp_id
    try:
        return tpl.format(**vars)
    except (KeyError, IndexError):
        return tpl


def _required_fields(vertical: str) -> list[str]:
    """從業務線 Pydantic Schema 推導必填字段（規則與 Schema 單一來源，避免兩處維護）。"""
    try:
        from app.schemas import Vertical, get_schema

        model = get_schema(Vertical(vertical))
        return [n for n, f in model.model_fields.items() if f.is_required()]
    except Exception:
        return []


def build_review(
    vertical: str,
    extracted: dict,
    enrichment: dict | None,
    decision: dict,
    trace: list | None = None,
    locale: str = "zh-HK",
) -> dict:
    """計算本作業的人工覆核級別與命中的檢查點列表。"""
    enrichment = enrichment or {}
    trace = trace or []
    checkpoints: list[dict] = []

    def add(cp_id: str, level: str, **vars: Any) -> None:
        checkpoints.append({
            "id": cp_id,
            "level": level,
            "label": (_LABEL.get(level) or {}).get(locale, level),
            "reason": _msg(cp_id, locale, **vars),
        })

    # CP-01 必填字段
    missing = [f for f in _required_fields(vertical) if extracted.get(f) in (None, "")]
    if missing:
        add("CP-01", "field", fields="、".join(missing[:6]))

    # CP-02 完整度
    completeness = enrichment.get("_completeness")
    if isinstance(completeness, (int, float)) and completeness < 0.8:
        add("CP-02", "field", completeness=completeness)

    # CP-03 UBO
    if vertical in ("family_office", "fund_ofc_lpf") and not extracted.get("受益所有人"):
        add("CP-03", "field")

    # CP-04 資金來源
    if vertical == "family_office" and not extracted.get("资金来源"):
        add("CP-04", "field")

    # CP-05 數據源降級（含 trace 中失敗的富集調用）
    degraded = [p for p in (enrichment.get("flags") or []) if "人工複核" in p or "人工" in p]
    failed = [t.get("name") for t in trace if t.get("kind") == "enrich" and not t.get("ok", True)]
    providers = [x for x in (degraded + [f for f in failed if f]) if x]
    if providers:
        add("CP-05", "source", providers="、".join(sorted(set(providers))[:5]))

    # CP-06 / CP-07 名單命中
    if enrichment.get("sanctions_hit"):
        add("CP-06", "gate")
    if enrichment.get("pep"):
        add("CP-07", "gate")

    # CP-08 風險帶位
    band = decision.get("risk_level") or decision.get("risk_band") or ""
    if band in ("high", "critical"):
        add("CP-08", "risk", band=band)

    # CP-09 critical 級規則
    critical = [h.get("id") for h in (decision.get("rules_hit") or []) if h.get("severity") == "critical"]
    if critical:
        add("CP-09", "gate", rules="、".join(critical[:5]))

    # CP-10 抽取兜底
    if any(t.get("kind") == "extract" and t.get("fallback") for t in trace):
        add("CP-10", "source")

    level = "none"
    for cp in checkpoints:
        if LEVEL_ORDER.get(cp["level"], 0) > LEVEL_ORDER.get(level, 0):
            level = cp["level"]

    return {
        "level": level,
        "required": level != "none",
        "checkpoints": checkpoints,
        "count": len(checkpoints),
        "levels": LEVEL_ORDER,
    }
