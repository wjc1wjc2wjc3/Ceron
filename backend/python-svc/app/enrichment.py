"""富集服务（Enrichment）：ICRIS 查冊、制裁/PEP 屏蔽、受益所有權核驗。

设计为**可插拔 Provider**：
- 默认 MockProvider（离线可跑，演示关键字规则）
- IcrisProvider / SanctionsProvider：在 .env 配置 API 地址与密钥后启用，
  调用失败时自动降级并打「需人工複核」标记，保证流水线不中断。
"""
from typing import Protocol

import httpx

from app.config import settings


class EnrichProvider(Protocol):
    name: str

    def enrich(self, vertical: str, extracted: dict) -> dict: ...


def _base_result(extracted: dict) -> dict:
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
        flags.append("PEP 命中：需加强尽调（EDD）。")
    keyword_hit = any(k in name for k in ("制裁", "受限制"))
    if keyword_hit:
        flags.append("制裁/受限制關鍵字命中：須人工複核並上報。")
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

    def enrich(self, vertical: str, extracted: dict) -> dict:
        return _base_result(extracted)


class IcrisProvider:
    """香港公司註冊處 ICRIS 查冊适配器。

    约定接口：POST {company_name} → {"verified": bool, "company_status": str}
    （真实接入需政府「大量查冊」核准与凭证；也可对接持牌数据服务商。）
    """

    name = "icris"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict) -> dict:
        result = _base_result(extracted)
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
            result["flags"].append("ICRIS 查冊失敗：需人工複核。")
            result["risk_from_enrich"] = "high"
        return result


class SanctionsProvider:
    """制裁/PEP 名单服务适配器。

    约定接口：POST {name} → {"hit": bool, "lists": [...]}
    （生产可对接 UN/EU/HK MAO 名单或持牌筛查服务商。）
    """

    name = "sanctions"

    def __init__(self, api_url: str, api_key: str) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict) -> dict:
        result = _base_result(extracted)
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
                result["flags"].append("制裁名單命中（外部服務）：直接拒絕並上報。")
                result["risk_from_enrich"] = "high"
        except Exception:
            result["flags"].append("制裁名單服務不可用：需人工複核。")
            result["risk_from_enrich"] = "high"
        return result


def get_enrich_provider() -> EnrichProvider:
    name = settings.enrichment_provider
    if name == "icris" and settings.icris_api_url:
        return IcrisProvider(settings.icris_api_url, settings.icris_api_key)
    if name == "sanctions" and settings.sanctions_api_url:
        return SanctionsProvider(settings.sanctions_api_url, settings.sanctions_api_key)
    return MockProvider()


def enrich(vertical: str, extracted: dict) -> dict:
    return get_enrich_provider().enrich(vertical, extracted)
