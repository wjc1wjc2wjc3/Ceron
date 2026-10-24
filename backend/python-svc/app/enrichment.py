"""富集服务（Enrichment）：ICRIS 查冊、制裁/PEP 屏蔽、土地註冊、信貸局、OFAC/HMT、CRS。

设计为**可插拔 Provider**：
- 默认 MockProvider（离线可跑，演示关键字规则）
- IcrisProvider / SanctionsProvider / LandRegistryProvider / CreditBureauProvider /
  OfacProvider / HmtProvider / CrsProvider：在 .env 配置对应 API 地址与密钥后启用，
  调用失败时自动降级并打「需人工複核」标记，保证流水线不中断。

所有面向用户的标记文案支持按 locale 本地化（zh-HK / en / zh-CN）。
"""
from typing import Protocol

import httpx

from app.config import settings


def tr(locale: str, hk: str, en: str, cn: str) -> str:
    """按 locale 返回对应语文的标记文案。"""
    return {"zh-HK": hk, "en": en, "zh-CN": cn}.get(locale, hk)


class EnrichProvider(Protocol):
    name: str

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict: ...


def _auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _post(api_url: str, api_key: str, payload: dict, timeout: float = 15.0) -> dict:
    resp = httpx.post(api_url, json=payload, headers=_auth_headers(api_key), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _base_result(extracted: dict, locale: str = "zh-HK") -> dict:
    """所有 Provider 共用的基线结果（基于抽取字段的本地规则）。"""
    flags: list[str] = []
    name = (
        extracted.get("客户姓名或实体名称")
        or extracted.get("投保人")
        or extracted.get("受保人")
        or ""
    )
    pep = extracted.get("是否政治公众人物PEP") in (True, "是", "true", "True")
    if pep:
        flags.append(
            tr(locale,
               "PEP 命中：需加強盡調（EDD）。",
               "PEP hit: enhanced due diligence (EDD) required.",
               "PEP 命中：需加强尽调（EDD）。")
        )
    keyword_hit = any(k in name for k in ("制裁", "受限制", "OFAC"))
    if keyword_hit:
        flags.append(
            tr(locale,
               "制裁/受限制關鍵字命中：須人工複核並上報。",
               "Sanctions/restricted keyword hit: manual review and report required.",
               "制裁/受限制关键字命中：须人工复核并上报。")
        )
    icris_verified = bool(extracted.get("统一社会信用代码") or extracted.get("保单号"))
    return {
        "provider": "mock",
        "icris_verified": icris_verified,
        "sanctions_hit": keyword_hit,
        "pep": pep,
        "credit_adverse": False,
        "land_unresolved": False,
        "crs_issue": False,
        "land_verified": False,
        "flags": flags,
        "risk_from_enrich": "high" if (pep or keyword_hit) else "normal",
    }


def _merge(result: dict, r: dict) -> None:
    """将单个 Provider 的贡献合并进总结果（flags 去重；布尔信号取 OR）。"""
    for f in r.get("flags", []):
        if f not in result["flags"]:
            result["flags"].append(f)
    if r.get("risk_from_enrich") == "high":
        result["risk_from_enrich"] = "high"
    for k in ("icris_verified", "sanctions_hit", "pep",
              "credit_adverse", "land_unresolved", "crs_issue", "land_verified"):
        if r.get(k):
            result[k] = True
    for k in ("sanctions_lists", "icris_company_status", "land_charges",
              "credit_score", "tax_residency", "fatca_status"):
        if r.get(k) is not None:
            result[k] = r[k]


class MockProvider:
    name = "mock"

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        return _base_result(extracted, locale)


class IcrisProvider:
    """香港公司註冊處 ICRIS 查冊适配器。

    约定接口：POST {company_name} → {"verified": bool, "company_status": str}
    （真实接入需政府「大量查冊」核准与凭证；也可对接持牌数据服务商。）
    """

    name = "icris"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "icris_verified": False}
        name = extracted.get("客户姓名或实体名称") or extracted.get("投保人") or ""
        if not name:
            return r
        if not self.api_url:
            r["icris_verified"] = True
            return r
        try:
            data = _post(self.api_url, self.api_key, {"company_name": name})
            r["icris_verified"] = bool(data.get("verified"))
            if data.get("company_status"):
                r["icris_company_status"] = data["company_status"]
        except Exception:
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "ICRIS 查冊失敗：需人工複核。",
                   "ICRIS lookup failed: manual review required.",
                   "ICRIS 查册失败：需人工复核。")
            )
        return r


class SanctionsProvider:
    """制裁/PEP 名单服务适配器（UN/EU/HK MAO 或持牌服务商）。"""

    name = "sanctions"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "sanctions_hit": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("投保人")
            or extracted.get("受益所有人")
            or ""
        )
        if not name:
            return r
        if not self.api_url:
            return r
        try:
            data = _post(self.api_url, self.api_key, {"name": name})
            if data.get("hit"):
                r["sanctions_hit"] = True
                r["risk_from_enrich"] = "high"
                r["sanctions_lists"] = data.get("lists", [])
                r["flags"].append(
                    tr(locale, "制裁名單命中（外部服務）：直接拒絕並上報。",
                       "Sanctions list hit (external): auto-reject and report.",
                       "制裁名单命中（外部服务）：直接拒绝并上报。")
                )
        except Exception:
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "制裁名單服務不可用：需人工複核。",
                   "Sanctions service unavailable: manual review required.",
                   "制裁名单服务不可用：需人工复核。")
            )
        return r


class LandRegistryProvider:
    """土地註冊處 Land Search 适配器（按揭物业产权/负擔查冊）。

    约定接口：POST {address, valuation} → {"verified": bool, "charges": [...]}
    （真实接入需政府查冊服务或持牌数据服务商。）
    """

    name = "land_search"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "land_unresolved": False}
        if extracted.get("物业估值港币万") is None and not extracted.get("物业类型"):
            return r  # 非物业类业务，跳过
        if not self.api_url:
            r["land_verified"] = True
            return r
        try:
            data = _post(self.api_url, self.api_key, {
                "address": extracted.get("物业类型"),
                "valuation": extracted.get("物业估值港币万"),
            })
            r["land_verified"] = bool(data.get("verified"))
            if data.get("charges"):
                r["land_charges"] = data["charges"]
            if not r["land_verified"] or data.get("charges"):
                r["land_unresolved"] = True
                r["risk_from_enrich"] = "high"
                r["flags"].append(
                    tr(locale, "土地註冊查冊未明 / 存在產權負擔，需核實。",
                       "Land search unresolved / encumbrances found; verification required.",
                       "土地注册查册未明 / 存在产权负担，需核实。")
                )
        except Exception:
            r["land_unresolved"] = True
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "土地註冊查冊失敗：需人工複核。",
                   "Land search failed: manual review required.",
                   "土地注册查册失败：需人工复核。")
            )
        return r


class CreditBureauProvider:
    """信贷局（TransUnion HK 等）适配器（信用评分 / 不利纪录）。"""

    name = "credit_bureau"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "credit_adverse": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("申请人")
            or extracted.get("投保人")
            or ""
        )
        if not name:
            return r
        if not self.api_url:
            r["credit_score"] = 720
            return r
        try:
            data = _post(self.api_url, self.api_key, {"name": name})
            r["credit_score"] = data.get("score")
            if data.get("adverse"):
                r["credit_adverse"] = True
                r["risk_from_enrich"] = "high"
                r["flags"].append(
                    tr(locale, "信貸局不利紀錄命中：需加強審查。",
                       "Adverse credit-bureau record hit: enhanced review required.",
                       "信贷局不利记录命中：需加强审查。")
                )
        except Exception:
            r["credit_adverse"] = True
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "信貸局查詢失敗：需人工複核。",
                   "Credit bureau lookup failed: manual review required.",
                   "信贷局查询失败：需人工复核。")
            )
        return r


class OfacProvider:
    """美国 OFAC SDN 名单筛查适配器。"""

    name = "ofac"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "sanctions_hit": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("受益人")
            or extracted.get("管理公司")
            or ""
        )
        if not name:
            return r
        if not self.api_url:
            if any(k in name for k in ("OFAC", "ofac")):
                r["sanctions_hit"] = True
                r["risk_from_enrich"] = "high"
                r["sanctions_lists"] = ["OFAC"]
                r["flags"].append(
                    tr(locale, "OFAC SDN 名單命中：直接拒絕並上報。",
                       "OFAC SDN list hit: auto-reject and report.",
                       "OFAC SDN 名单命中：直接拒绝并上报。")
                )
            return r
        try:
            data = _post(self.api_url, self.api_key, {"name": name})
            if data.get("hit"):
                r["sanctions_hit"] = True
                r["risk_from_enrich"] = "high"
                r["sanctions_lists"] = data.get("lists", ["OFAC"])
                r["flags"].append(
                    tr(locale, "OFAC SDN 名單命中：直接拒絕並上報。",
                       "OFAC SDN list hit: auto-reject and report.",
                       "OFAC SDN 名单命中：直接拒绝并上报。")
                )
        except Exception:
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "OFAC 名單服務不可用：需人工複核。",
                   "OFAC list service unavailable: manual review required.",
                   "OFAC 名单服务不可用：需人工复核。")
            )
        return r


class HmtProvider:
    """英国 HMT 综合制裁名单筛查适配器。"""

    name = "hmt"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "sanctions_hit": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("受益人")
            or extracted.get("管理公司")
            or ""
        )
        if not name:
            return r
        if not self.api_url:
            if any(k in name for k in ("HMT", "hmt")):
                r["sanctions_hit"] = True
                r["risk_from_enrich"] = "high"
                r["sanctions_lists"] = ["HMT"]
                r["flags"].append(
                    tr(locale, "HMT 綜合名單命中：直接拒絕並上報。",
                       "HMT consolidated list hit: auto-reject and report.",
                       "HMT 综合名单命中：直接拒绝并上报。")
                )
            return r
        try:
            data = _post(self.api_url, self.api_key, {"name": name})
            if data.get("hit"):
                r["sanctions_hit"] = True
                r["risk_from_enrich"] = "high"
                r["sanctions_lists"] = data.get("lists", ["HMT"])
                r["flags"].append(
                    tr(locale, "HMT 綜合名單命中：直接拒絕並上報。",
                       "HMT consolidated list hit: auto-reject and report.",
                       "HMT 综合名单命中：直接拒绝并上报。")
                )
        except Exception:
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "HMT 名單服務不可用：需人工複核。",
                   "HMT list service unavailable: manual review required.",
                   "HMT 名单服务不可用：需人工复核。")
            )
        return r


class CrsProvider:
    """CRS / FATCA 税务居民信息自动交换核查适配器。"""

    name = "crs"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "crs_issue": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("受益所有人")
            or ""
        )
        if not name:
            return r
        if not self.api_url:
            r["tax_residency"] = "HK"
            r["fatca_status"] = "compliant"
            return r
        try:
            data = _post(self.api_url, self.api_key, {"name": name})
            r["tax_residency"] = data.get("tax_residency")
            if data.get("fatca_status") != "compliant":
                r["crs_issue"] = True
                r["risk_from_enrich"] = "high"
                r["flags"].append(
                    tr(locale, "CRS/FATCA 稅務居民狀態異常，需核實。",
                       "CRS/FATCA tax-residency status anomaly; verification required.",
                       "CRS/FATCA 税务居民状态异常，需核实。")
                )
        except Exception:
            r["crs_issue"] = True
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "CRS/FATCA 查詢失敗：需人工複核。",
                   "CRS/FATCA lookup failed: manual review required.",
                   "CRS/FATCA 查询失败：需人工复核。")
            )
        return r


def get_enrich_provider() -> EnrichProvider:
    name = settings.enrichment_provider
    if name == "icris" and settings.icris_api_url:
        return IcrisProvider(settings.icris_api_url, settings.icris_api_key)
    if name == "sanctions" and settings.sanctions_api_url:
        return SanctionsProvider(settings.sanctions_api_url, settings.sanctions_api_key)
    return MockProvider()


def get_configured_providers() -> list:
    """按 .env 中已配置的 API_URL 实例化全部启用的 Provider。"""
    provs: list = []
    if settings.icris_api_url:
        provs.append(IcrisProvider(settings.icris_api_url, settings.icris_api_key))
    if settings.sanctions_api_url:
        provs.append(SanctionsProvider(settings.sanctions_api_url, settings.sanctions_api_key))
    if settings.land_search_api_url:
        provs.append(LandRegistryProvider(settings.land_search_api_url, settings.land_search_api_key))
    if settings.credit_bureau_api_url:
        provs.append(CreditBureauProvider(settings.credit_bureau_api_url, settings.credit_bureau_api_key))
    if settings.ofac_api_url:
        provs.append(OfacProvider(settings.ofac_api_url, settings.ofac_api_key))
    if settings.hmt_api_url:
        provs.append(HmtProvider(settings.hmt_api_url, settings.hmt_api_key))
    if settings.crs_api_url:
        provs.append(CrsProvider(settings.crs_api_url, settings.crs_api_key))
    return provs


def enrich(vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
    """运行全部已配置的富集 Provider，与 mock 基线合并。

    当 .env 配置了对应 *_API_URL 时，对应 Provider 会被实际调用；
    任一外部源调用失败均自动降级并打「需人工複核」标记，流水线不中断。
    全部未配置时退化为 mock 基线（离线可跑）。
    """
    result = _base_result(extracted, locale)
    providers = get_configured_providers()
    if not providers:
        return result
    result["provider"] = "+".join(p.name for p in providers)
    for p in providers:
        _merge(result, p.enrich(vertical, extracted, locale))
    return result
