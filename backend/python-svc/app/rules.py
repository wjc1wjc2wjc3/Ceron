"""合規閘口規則包（Rule Pack）：把決策引擎的判斷條件從硬編碼 if/elif 抽成**可版本化、可導出、可 diff** 的規則表。

設計要點（借鑒 Marble 的 scenario/rule + rule execution 記錄、kyc-analyst 的確定性評分）：
- 每條規則有穩定 ``id``、所屬監管閘口 ``gate``、加權分 ``delta``、嚴重度 ``severity`` 與三語理由；
- ``evaluate()`` 除了分數與理由，還返回結構化的 ``hits``（規則執行記錄），供審計包與前端追溯；
- ``RULE_PACK_VERSION`` 隨規則內容變更而遞增，決策結果會帶上 ``rule_pack`` 版本，
  換模型/換部署都不影響審計口徑（模型是零件，規則與證據鏈才是資產）。
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# 規則包版本：規則內容有任何變更（新增/刪除/改分/改文案）都必須遞增，
# 使歷史決策可以回溯到當時生效的規則版本。
RULE_PACK_VERSION = "2026.10.1"

_RISK_ORDER = {"低": 1, "中": 2, "高": 3}


def _risk_level(v: object) -> int:
    if isinstance(v, str) and v in _RISK_ORDER:
        return _RISK_ORDER[v]
    return 0


def _num(v: object) -> Optional[float]:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Rule:
    id: str
    gate: str                      # IA | SFC | HKMA | MPFA | AML | CDD | DATA
    vertical: str                  # 業務線；"*" 表示通用
    severity: str                  # low | medium | high | critical
    delta: int                     # 命中後累加的風險分
    test: Callable[[dict, dict], bool]
    reason: dict = field(default_factory=dict)   # {"zh-HK","en","zh-CN"}，可含 {占位符}
    fields: tuple = ()             # 規則依賴的抽取字段（供審計與缺失分析）

    def text(self, locale: str, **vars: Any) -> str:
        tpl = self.reason.get(locale) or self.reason.get("zh-HK") or self.id
        try:
            return tpl.format(**vars)
        except (KeyError, IndexError):
            return tpl


def _has(v: object) -> bool:
    return v not in (None, "", [])


# ============ 規則表（順序即審計中的命中順序，勿隨意調整）============
RULES: list[Rule] = [
    # ---- 通用：資料完整度 ----
    Rule(
        id="DATA.completeness.low",
        gate="DATA", vertical="*", severity="high", delta=40,
        test=lambda e, g: (g.get("_completeness") or 0) < 0.5,
        reason={
            "zh-HK": "資料完整度偏低（{completeness}），需補充材料。",
            "en": "Low data completeness ({completeness}); additional documents required.",
            "zh-CN": "资料完整度偏低（{completeness}），需补充材料。",
        },
    ),

    # ---- 港股保險 / 承保理賠（保監局 IA）----
    Rule(
        id="IA.insurance.completeness",
        gate="IA", vertical="insurance_hk", severity="medium", delta=20,
        test=lambda e, g: _num(e.get("资料完整度")) is not None and _num(e.get("资料完整度")) < 0.8,
        reason={
            "zh-HK": "理賠資料不完整，存在核查必要。",
            "en": "Incomplete claim documents; verification required.",
            "zh-CN": "理赔资料不完整，存在核查必要。",
        },
        fields=("资料完整度",),
    ),
    Rule(
        id="IA.insurance.claim_near_sum_assured",
        gate="IA", vertical="insurance_hk", severity="high", delta=25,
        test=lambda e, g: bool(
            (_num(e.get("保额港币万")) or 0)
            and (_num(e.get("理赔金额港币万")) or 0)
            and (_num(e.get("理赔金额港币万")) / _num(e.get("保额港币万"))) > 0.8
        ),
        reason={
            "zh-HK": "理賠金額接近保額，殘值/道德風險偏高。",
            "en": "Claim amount is close to sum assured; elevated moral-hazard risk.",
            "zh-CN": "理赔金额接近保额，残值/道德风险偏高。",
        },
        fields=("保额港币万", "理赔金额港币万"),
    ),

    # ---- 家族辦公室 KYC（CDD / AML）----
    Rule(
        id="CDD.family_office.source_of_funds",
        gate="CDD", vertical="family_office", severity="medium", delta=20,
        test=lambda e, g: not _has(e.get("资金来源")),
        reason={
            "zh-HK": "缺少資金來源說明，CDD 不完整。",
            "en": "Missing source-of-funds explanation; CDD incomplete.",
            "zh-CN": "缺少资金来源说明，CDD 不完整。",
        },
        fields=("资金来源",),
    ),
    Rule(
        id="CDD.family_office.kyc_incomplete",
        gate="CDD", vertical="family_office", severity="medium", delta=15,
        test=lambda e, g: e.get("KYC状态") in ("待补", "未完成"),
        reason={
            "zh-HK": "KYC 未完成。",
            "en": "KYC not completed.",
            "zh-CN": "KYC 未完成。",
        },
        fields=("KYC状态",),
    ),

    # ---- 銀行按揭承保（HKMA）----
    Rule(
        id="HKMA.mortgage.ltv_above_cap",
        gate="HKMA", vertical="banking_mortgage", severity="high", delta=30,
        test=lambda e, g: _num(e.get("贷款成数LTV")) is not None and _num(e.get("贷款成数LTV")) > 0.6,
        reason={
            "zh-HK": "按揭成數(LTV)超 HKMA 上限 60%，需按揭保險或加壓力測試。",
            "en": "Loan-to-value (LTV) exceeds the HKMA 60% cap; mortgage insurance or stress test required.",
            "zh-CN": "按揭成数(LTV)超 HKMA 上限 60%，需按揭保险或加压力测试。",
        },
        fields=("贷款成数LTV",),
    ),
    Rule(
        id="HKMA.mortgage.dsr_above_cap",
        gate="HKMA", vertical="banking_mortgage", severity="high", delta=25,
        test=lambda e, g: _num(e.get("供款入息比率DSR")) is not None and _num(e.get("供款入息比率DSR")) > 0.5,
        reason={
            "zh-HK": "供款入息比率(DSR)超 50%，還款能力存疑。",
            "en": "Debt-servicing ratio (DSR) exceeds 50%; repayment capacity questionable.",
            "zh-CN": "供款入息比率(DSR)超 50%，还款能力存疑。",
        },
        fields=("供款入息比率DSR",),
    ),
    Rule(
        id="CDD.mortgage.down_payment_source",
        gate="CDD", vertical="banking_mortgage", severity="medium", delta=15,
        test=lambda e, g: not _has(e.get("首期资金来源")),
        reason={
            "zh-HK": "缺少首期資金來源說明，CDD 不完整。",
            "en": "Missing source-of-down-payment explanation; CDD incomplete.",
            "zh-CN": "缺少首期资金来源说明，CDD 不完整。",
        },
        fields=("首期资金来源",),
    ),

    # ---- 證券合適性（SFC）----
    Rule(
        id="SFC.suitability.risk_mismatch",
        gate="SFC", vertical="securities_suitability", severity="high", delta=35,
        test=lambda e, g: bool(
            _risk_level(e.get("风险承受度"))
            and _risk_level(e.get("产品风险等级"))
            and _risk_level(e.get("产品风险等级")) > _risk_level(e.get("风险承受度"))
        ),
        reason={
            "zh-HK": "產品風險超出客戶風險承受度，存在不適合性 / 誤售風險。",
            "en": "Product risk exceeds client's risk tolerance; unsuitability / mis-selling risk.",
            "zh-CN": "产品风险超出客户风险承受度，存在不适合性 / 误售风险。",
        },
        fields=("风险承受度", "产品风险等级"),
    ),
    Rule(
        id="SFC.suitability.high_risk_inexperienced",
        gate="SFC", vertical="securities_suitability", severity="medium", delta=20,
        test=lambda e, g: _risk_level(e.get("产品风险等级")) == 3
        and _num(e.get("投资经验年")) is not None
        and _num(e.get("投资经验年")) < 2,
        reason={
            "zh-HK": "高風險產品但投資經驗不足，需加強風險揭示。",
            "en": "High-risk product but insufficient investment experience; enhance risk disclosure.",
            "zh-CN": "高风险产品但投资经验不足，需加强风险揭示。",
        },
        fields=("产品风险等级", "投资经验年"),
    ),

    # ---- 強積金（MPFA）----
    Rule(
        id="MPFA.employer_not_registered",
        gate="MPFA", vertical="mpf", severity="high", delta=30,
        test=lambda e, g: e.get("雇主登记状态") == "未登记",
        reason={
            "zh-HK": "僱主未登記強積金計劃，違反 MPFA 合規。",
            "en": "Employer not registered for MPF scheme; MPFA non-compliance.",
            "zh-CN": "雇主未登记强积金计划，违反 MPFA 合规。",
        },
        fields=("雇主登记状态",),
    ),
    Rule(
        id="MPFA.employee_status_ineligible",
        gate="MPFA", vertical="mpf", severity="medium", delta=20,
        test=lambda e, g: e.get("雇员状态") not in (None, "", "在职", "自雇"),
        reason={
            "zh-HK": "僱員狀態不符供款資格。",
            "en": "Employee status does not meet contribution eligibility.",
            "zh-CN": "雇员状态不符供款资格。",
        },
        fields=("雇员状态",),
    ),
    Rule(
        id="MPFA.contribution_overdue",
        gate="MPFA", vertical="mpf", severity="medium", delta=15,
        test=lambda e, g: e.get("供款状态") == "逾期",
        reason={
            "zh-HK": "供款逾期，需跟進。",
            "en": "Contributions overdue; follow-up required.",
            "zh-CN": "供款逾期，需跟进。",
        },
        fields=("供款状态",),
    ),

    # ---- 基金 OFC / LPF（SFC Type 9）----
    Rule(
        id="SFC.fund.unauthorized_retail",
        gate="SFC", vertical="fund_ofc_lpf", severity="critical", delta=40,
        test=lambda e, g: e.get("是否获证监会认可") == "否" and e.get("投资者类型") == "零售",
        reason={
            "zh-HK": "未獲證監會認可卻面向零售投資者，違規。",
            "en": "Not SFC-authorized yet offered to retail investors; non-compliant.",
            "zh-CN": "未获证监会认可却面向零售投资者，违规。",
        },
        fields=("是否获证监会认可", "投资者类型"),
    ),
    Rule(
        id="CDD.fund.beneficial_owner_missing",
        gate="CDD", vertical="fund_ofc_lpf", severity="medium", delta=20,
        test=lambda e, g: not _has(e.get("受益所有人")),
        reason={
            "zh-HK": "缺少受益所有人，CDD 不完整。",
            "en": "Missing beneficial owner; CDD incomplete.",
            "zh-CN": "缺少受益所有人，CDD 不完整。",
        },
        fields=("受益所有人",),
    ),
    Rule(
        id="SFC.fund.manager_missing",
        gate="SFC", vertical="fund_ofc_lpf", severity="medium", delta=15,
        test=lambda e, g: e.get("结构类型") in ("OFC", "LPF", "REIT") and not _has(e.get("管理公司")),
        reason={
            "zh-HK": "基金結構已聲明但管理公司缺失，需補正。",
            "en": "Fund structure stated but manager missing; needs completion.",
            "zh-CN": "基金结构已声明但管理公司缺失，需补正。",
        },
        fields=("结构类型", "管理公司"),
    ),

    # ---- 富集信號（AML / CFT）----
    Rule(
        id="AML.sanctions_hit",
        gate="AML", vertical="*", severity="critical", delta=60,
        test=lambda e, g: bool(g.get("sanctions_hit")),
        reason={
            "zh-HK": "制裁名單命中，直接拒絕並上報。",
            "en": "Sanctions list hit: auto-reject and report.",
            "zh-CN": "制裁名单命中，直接拒绝并上报。",
        },
    ),
    Rule(
        id="AML.pep",
        gate="AML", vertical="*", severity="medium", delta=20,
        test=lambda e, g: bool(g.get("pep")),
        reason={
            "zh-HK": "PEP：需加強盡調。",
            "en": "PEP: enhanced due diligence required.",
            "zh-CN": "PEP：需加强尽调。",
        },
    ),
    Rule(
        id="AML.credit_adverse",
        gate="AML", vertical="*", severity="high", delta=30,
        test=lambda e, g: bool(g.get("credit_adverse")),
        reason={
            "zh-HK": "信貸局不利紀錄：需加強審查。",
            "en": "Adverse credit-bureau record: enhanced review required.",
            "zh-CN": "信贷局不利记录：需加强审查。",
        },
    ),
    Rule(
        id="AML.land_unresolved",
        gate="AML", vertical="*", severity="medium", delta=20,
        test=lambda e, g: bool(g.get("land_unresolved")),
        reason={
            "zh-HK": "土地註冊查冊未明：產權核實必要。",
            "en": "Land search unresolved; property title verification required.",
            "zh-CN": "土地注册查册未明：产权核实必要。",
        },
    ),
    Rule(
        id="AML.crs_issue",
        gate="AML", vertical="*", severity="medium", delta=15,
        test=lambda e, g: bool(g.get("crs_issue")),
        reason={
            "zh-HK": "CRS/FATCA 稅務居民狀態異常。",
            "en": "CRS/FATCA tax-residency status anomaly.",
            "zh-CN": "CRS/FATCA 税务居民状态异常。",
        },
    ),
]


RISK_BANDS = [
    # (下界, band, action)：借鑒 kyc-analyst 的分層（低/中/高/critical → 不同處置）
    (80, "critical", "reject"),
    (60, "high", "reject"),
    (25, "medium", "manual_review"),
    (0, "low", "approve"),
]


def band_of(score: int) -> tuple[str, str]:
    for lower, band, action in RISK_BANDS:
        if score >= lower:
            return band, action
    return "low", "approve"


def evaluate(
    vertical: str,
    extracted: dict,
    enrichment: dict | None = None,
    locale: str = "zh-HK",
    completeness: float = 1.0,
) -> dict:
    """跑規則包，返回結構化的規則執行記錄（供審計與前端展示）。"""
    enrichment = enrichment or {}
    # 供通用規則使用的上下文（完整度由決策層算好後傳入，保證與回傳值一致）
    ctx = dict(enrichment)
    ctx["_completeness"] = completeness

    hits: list[dict] = []
    reasons: list[str] = []
    score = 0
    for rule in RULES:
        if rule.vertical not in ("*", vertical):
            continue
        try:
            matched = bool(rule.test(extracted, ctx))
        except Exception:
            matched = False  # 單條規則異常不影響整條流水線
        if not matched:
            continue
        score += rule.delta
        text = rule.text(locale, completeness=completeness)
        reasons.append(text)
        hits.append({
            "id": rule.id,
            "gate": rule.gate,
            "vertical": rule.vertical,
            "severity": rule.severity,
            "delta": rule.delta,
            "reason": text,
            "fields": [f for f in rule.fields if f in extracted],
        })
    return {"score": score, "hits": hits, "reasons": reasons}


def export(version: str | None = None) -> dict:
    """導出規則包（供合規審閱 / 版本比對 / 客戶自檢）。"""
    return {
        "version": RULE_PACK_VERSION,
        "requested_version": version or RULE_PACK_VERSION,
        "count": len(RULES),
        "gates": sorted({r.gate for r in RULES}),
        "verticals": sorted({r.vertical for r in RULES if r.vertical != "*"}),
        "rules": [
            {
                "id": r.id,
                "gate": r.gate,
                "vertical": r.vertical,
                "severity": r.severity,
                "delta": r.delta,
                "fields": list(r.fields),
                "reason": r.reason,
            }
            for r in RULES
        ],
    }
