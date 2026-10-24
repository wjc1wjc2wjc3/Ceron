"""富集服务（Enrichment）：ICRIS 查冊、制裁/PEP 屏蔽、受益所有權核驗。

设计为**可插拔 Provider**：
- 默认 MockProvider（离线可跑，演示关键字规则）
- IcrisProvider / SanctionsProvider：在 .env 配置 API 地址与密钥后启用，
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
    keyword_hit = any(k in name for k in ("制裁", "受限制"))
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
        "flags": flags,
        "risk_from_enrich": "high" if (pep or keyword_hit) else "normal",
    }


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
        result = _base_result(extracted, locale)
        result["provider"] = self.name
        name = extracted.get("客户姓名或实体名称") or extracted.get("投保人") or ""
        if not name:
            return result
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            resp = httpx.post(self.api_url, json={"company_name": name},
                              headers=headers, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
            result["icris_verified"] = bool(data.get("verified"))
            if data.get("company_status"):
                result["icris_company_status"] = data["company_status"]
        except Exception:
            result["flags"].append(
                tr(locale,
                   "ICRIS 查冊失敗：需人工複核。",
                   "ICRIS lookup failed: manual review required.",
                   "ICRIS 查册失败：需人工复核。")
            )
            result["risk_from_enrich"] = "high"
        return result


class SanctionsProvider:
    """制裁/PEP 名单服务适配器。

    约定接口：POST {name} → {"hit": bool, "lists": [...]}
    （生产可对接 UN/EU/HK MAO 名单或持牌筛查服务商；优先级 1 将补全 OFAC/HMT/FATF 灰名单。）
    """

    name = "sanctions"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        result = _base_result(extracted, locale)
        result["provider"] = self.name
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("投保人")
            or extracted.get("受益所有人")
            or ""
        )
        if not name:
            return result
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            resp = httpx.post(self.api_url, json={"name": name},
                              headers=headers, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
            result["sanctions_hit"] = bool(data.get("hit"))
            if data.get("lists"):
                result["sanctions_lists"] = data["lists"]
            if result["sanctions_hit"]:
                result["flags"].append(
                    tr(locale,
                       "制裁名單命中（外部服務）：直接拒絕並上報。",
                       "Sanctions list hit (external): auto-reject and report.",
                       "制裁名单命中（外部服务）：直接拒绝并上报。")
                )
                result["risk_from_enrich"] = "high"
        except Exception:
            result["flags"].append(
                tr(locale,
                   "制裁名單服務不可用：需人工複核。",
                   "Sanctions service unavailable: manual review required.",
                   "制裁名单服务不可用：需人工复核。")
            )
            result["risk_from_enrich"] = "high"
        return result


def get_enrich_provider() -> EnrichProvider:
    name = settings.enrichment_provider
    if name == "icris" and settings.icris_api_url:
        return IcrisProvider(settings.icris_api_url, settings.icris_api_key)
    if name == "sanctions" and settings.sanctions_api_url:
        return SanctionsProvider(settings.sanctions_api_url, settings.sanctions_api_key)
    return MockProvider()


def enrich(vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
    """运行全部已配置的富集 Provider（ICRIS / 制裁名单），与 mock 基线合并。

    当 .env 配置了 ICRIS_API_URL / SANCTIONS_API_URL 时，对应 Provider 会被实际调用；
    任一外部源调用失败均自动降级并打「需人工複核」标记，流水线不中断。
    两者均未配置时退化为 mock 基线（离线可跑）。
    """
    result = _base_result(extracted, locale)
    providers: list = []
    if settings.icris_api_url:
        providers.append(IcrisProvider(settings.icris_api_url, settings.icris_api_key))
    if settings.sanctions_api_url:
        providers.append(SanctionsProvider(settings.sanctions_api_url, settings.sanctions_api_key))
    if not providers:
        return result

    result["provider"] = "+".join(p.name for p in providers)
    for p in providers:
        r = p.enrich(vertical, extracted, locale)
        result["icris_verified"] = result["icris_verified"] or r.get("icris_verified", False)
        result["sanctions_hit"] = result["sanctions_hit"] or r.get("sanctions_hit", False)
        for f in r.get("flags", []):
            if f not in result["flags"]:
                result["flags"].append(f)
        if r.get("icris_company_status"):
            result["icris_company_status"] = r["icris_company_status"]
        if r.get("sanctions_lists"):
            result["sanctions_lists"] = r["sanctions_lists"]
        if r.get("risk_from_enrich") == "high":
            result["risk_from_enrich"] = "high"
    return result
