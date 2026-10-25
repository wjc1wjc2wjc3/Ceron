"""富集服务（Enrichment）：ICRIS 查冊、制裁/PEP 屏蔽、土地註冊、信貸局、OFAC/HMT、CRS。

设计为**可插拔 Provider**：
- 默认 MockProvider（离线可跑，演示关键字规则）
- IcrisProvider / SanctionsProvider / LandRegistryProvider / CreditBureauProvider /
  OfacProvider / HmtProvider / CrsProvider：在 .env 配置对应 API 地址与密钥后启用，
  调用失败时自动降级并打「需人工複核」标记，保证流水线不中断。

所有面向用户的标记文案支持按 locale 本地化（zh-HK / en / zh-CN）。
"""
import re
import time
from typing import Optional, Protocol

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


def _get(api_url: str, api_key: str, params: dict | None = None, token: str | None = None,
         timeout: float = 15.0) -> dict:
    headers = _auth_headers(api_key)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = httpx.get(api_url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _login(auth_url: str, account: str, api_key: str, timeout: float = 15.0) -> str | None:
    """向数据源鉴权端点换取会话令牌（ICRIS 等需登录态的服务）。"""
    resp = httpx.post(auth_url, json={"account": account, "api_key": api_key}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data.get("access_token") or data.get("token")


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
    for k in ("icris_verified", "sanctions_hit", "pep", "icij_hit",
              "credit_adverse", "land_unresolved", "crs_issue", "land_verified"):
        if r.get(k):
            result[k] = True
    for k in ("sanctions_lists", "pep_lists", "icris_company_status", "icris_br_status",
              "icris_cr_no", "land_charges", "icij_entities",
              "credit_score", "tax_residency", "fatca_status"):
        if r.get(k) is not None:
            result[k] = r[k]


class MockProvider:
    name = "mock"

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        return _base_result(extracted, locale)


class IcrisProvider:
    """香港公司註冊處 ICRIS 查冊适配器（真实接入）。

    支持两种接入形态：
    1. 会话态（推荐，需 ICRIS_AUTH_URL）：先向鉴权端点换 token，再以 Bearer
       令牌 GET 查询（兼容 ICRIS e-Services / 持牌数据服务商的 JSON 契约）。
    2. 直连态：按既有契约 POST 查询（与旧版 mock/占位行为一致）。

    密钥来自 .env：ICRIS_API_URL / ICRIS_API_KEY / ICRIS_AUTH_URL / ICRIS_ACCOUNT。
    仅当 ICRIS_API_URL 配置时才会真正外呼；未配置退化为离线演示（verified=True）。
    调用失败一律降级并打「需人工複核」标记，流水线不中断。
    """

    name = "icris"

    def __init__(self, api_url: str, api_key: str = "", auth_url: str = "",
                 account: str = "") -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.auth_url = auth_url
        self.account = account

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "icris_verified": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("投保人")
            or extracted.get("公司名称")
            or ""
        )
        cr_no = (
            extracted.get("公司编号") or extracted.get("CR No") or extracted.get("CR號碼") or ""
        )
        if not name and not cr_no:
            return r
        if not self.api_url:
            r["icris_verified"] = True  # 离线演示
            return r
        try:
            token = None
            if self.auth_url:
                token = _login(self.auth_url, self.account, self.api_key)
            params = {}
            if cr_no:
                params["cr_no"] = cr_no
            else:
                params["name"] = name
            if token:
                data = _get(self.api_url, "", params=params, token=token)
            else:
                body = {"company_name": name} if name else {"cr_no": cr_no}
                data = _post(self.api_url, self.api_key, body)
            r["icris_verified"] = bool(data.get("verified"))
            if data.get("company_status"):
                r["icris_company_status"] = data["company_status"]
            if data.get("br_status"):
                r["icris_br_status"] = data["br_status"]
            r["icris_cr_no"] = data.get("cr_no") or cr_no
            if data.get("dissolved") or data.get("company_status") in (
                "Dissolved", "Deregistered", "已解散", "已撤銷註冊"
            ):
                r["risk_from_enrich"] = "high"
                r["flags"].append(
                    tr(locale, "ICRIS：公司已解散／撤銷註冊，需核查。",
                       "ICRIS: company dissolved / deregistered; verification required.",
                       "ICRIS：公司已解散／撤销注册，需核查。")
                )
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
    """信贷局（TransUnion HK 等会员机构）适配器（信用评分 / 不利纪录）。

    真实接入：以会员编号（X-Member-Id）+ API Key 调用信贷局信用报告接口
    （多数为相互 TLS + 会员鉴权；此处以 HTTP Header 透传会员标识与密钥）。
    密钥来自 .env：CREDIT_BUREAU_API_URL / CREDIT_BUREAU_API_KEY / CREDIT_BUREAU_MEMBER_ID。
    未配置 CREDIT_BUREAU_API_URL 时退化为离线演示（credit_score=720）。
    调用失败一律降级并打「需人工複核」标记。
    """

    name = "credit_bureau"

    def __init__(self, api_url: str, api_key: str = "", member_id: str = "") -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.member_id = member_id

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "credit_adverse": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("申请人")
            or extracted.get("投保人")
            or ""
        )
        hkid = extracted.get("香港身份證") or extracted.get("HKID") or ""
        if not name:
            return r
        if not self.api_url:
            r["credit_score"] = 720  # 离线演示
            return r
        try:
            headers = _auth_headers(self.api_key)
            if self.member_id:
                headers["X-Member-Id"] = self.member_id
            resp = httpx.post(
                self.api_url,
                json={"name": name, "hkid": hkid},
                headers=headers,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            r["credit_score"] = data.get("score")
            if data.get("adverse") or data.get("adverse_records"):
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


class IcijProvider:
    """ICIJ Offshore Leaks（巴拿马/天堂/潘多拉文件）公开数据库筛查适配器。

    借鉴 kyc-analyst 的免费公开数据源思路：ICIJ 离岸资料库对香港家办/信托
    尽调极有价值（离岸持股结构透明化），且**公开站点可直接查、无需密钥**，
    因此默认 ``https://offshoreleaks.icij.org/search`` 开箱即用。

    两种接入形态：
    1. 默认公开站点：GET 站内搜索，解析命中实体（名称/实体链接）；
    2. 自建索引：配置 ICIJ_API_URL 指向内部 JSON 服务（POST {"name": ...} 契约）。

    配置 ICIJ_API_URL="" 可整体停用。失败一律降级打「需人工複核」，不中断流水线。
    """

    name = "icij"

    _ENTITY_RE = re.compile(r'href="/(?:entities|officers|intermediaries)/\d+"[^>]*>([^<]{2,120})<')

    def __init__(self, api_url: str, api_key: str = "") -> None:
        self.api_url = api_url
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "icij_hit": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("受益所有人")
            or extracted.get("管理公司")
            or extracted.get("投保人")
            or ""
        )
        if not name or not self.api_url:
            return r
        try:
            if self.api_url.rstrip("/").endswith("/search"):
                # 公开站点 HTML 搜索（仅取命中实体名，用于人工核查线索）
                resp = httpx.get(
                    self.api_url, params={"q": name},
                    headers={"User-Agent": "Ceron-Compliance/1.0"},
                    timeout=20.0,
                )
                resp.raise_for_status()
                entities = []
                seen = set()
                for m in self._ENTITY_RE.finditer(resp.text):
                    n = m.group(1).strip()
                    if n and n not in seen:
                        seen.add(n)
                        entities.append(n)
                    if len(entities) >= 5:
                        break
            else:
                data = _post(self.api_url, self.api_key, {"name": name})
                entities = list(data.get("entities") or [])
            if entities:
                r["icij_hit"] = True
                r["icij_entities"] = entities
                r["risk_from_enrich"] = "high"
                r["flags"].append(
                    tr(locale,
                       "ICIJ 離岸資料庫命中：需人工核查持股/代名安排。",
                       "ICIJ Offshore Leaks hit: manual verification of ownership/nominee arrangements required.",
                       "ICIJ 离岸资料库命中：需人工核查持股/代名安排。")
                )
        except Exception:
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "ICIJ 離岸資料庫查詢失敗：需人工複核。",
                   "ICIJ Offshore Leaks lookup failed: manual review required.",
                   "ICIJ 离岸资料库查询失败：需人工复核。")
            )
        return r


class OpenSanctionsPepProvider:
    """OpenSanctions PEP 筛查适配器（100+ 国家政治公众人物，免费公开数据）。

    支持官方 API（api.opensanctions.org，需 key）与自托管 yente
    （OPENSANCTIONS_API_URL=http://localhost:8001 等）两种部署：
    GET {base}/search/default?q={name}&limit=5 → {"results": [{name, score, datasets}]}
    命中 pep 类数据集 → PED/PEP 加強盡調；命中 sanctions 类数据集 → 直接拒絕並上報。
    """

    name = "opensanctions_pep"

    def __init__(self, api_url: str, api_key: str = "") -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    def enrich(self, vertical: str, extracted: dict, locale: str = "zh-HK") -> dict:
        r = {"flags": [], "risk_from_enrich": "normal", "sanctions_hit": False, "pep": False}
        name = (
            extracted.get("客户姓名或实体名称")
            or extracted.get("受益所有人")
            or extracted.get("投保人")
            or ""
        )
        if not name or not self.api_url:
            return r
        try:
            data = _get(f"{self.api_url}/search/default", self.api_key,
                        params={"q": name, "limit": 5})
            pep_lists, sanction_lists = [], []
            for item in data.get("results") or []:
                if float(item.get("score") or 0) < 0.5:
                    continue  # 低相关度不算命中（同名噪音）
                datasets = item.get("datasets") or [item.get("dataset")] or []
                ds = " ".join(str(d) for d in datasets).lower()
                if "pep" in ds or "ped" in ds:
                    pep_lists.append(item.get("name") or item.get("id"))
                if "sanction" in ds:
                    sanction_lists.append(item.get("name") or item.get("id"))
            if pep_lists:
                r["pep"] = True
                r["risk_from_enrich"] = "high"
                r["pep_lists"] = pep_lists[:5]
                r["flags"].append(
                    tr(locale, "OpenSanctions PEP 命中：需加強盡調（EDD）。",
                       "OpenSanctions PEP hit: enhanced due diligence (EDD) required.",
                       "OpenSanctions PEP 命中：需加强尽调（EDD）。")
                )
            if sanction_lists:
                r["sanctions_hit"] = True
                r["risk_from_enrich"] = "high"
                r["sanctions_lists"] = (r.get("sanctions_lists") or []) + sanction_lists[:5]
                r["flags"].append(
                    tr(locale, "OpenSanctions 制裁名單命中：直接拒絕並上報。",
                       "OpenSanctions sanctions hit: auto-reject and report.",
                       "OpenSanctions 制裁名单命中：直接拒绝并上报。")
                )
        except Exception:
            r["risk_from_enrich"] = "high"
            r["flags"].append(
                tr(locale, "OpenSanctions 查詢失敗：需人工複核。",
                   "OpenSanctions lookup failed: manual review required.",
                   "OpenSanctions 查询失败：需人工复核。")
            )
        return r


def get_enrich_provider() -> EnrichProvider:
    name = settings.enrichment_provider
    if name == "icris" and settings.icris_api_url:
        return IcrisProvider(
            settings.icris_api_url, settings.icris_api_key,
            settings.icris_auth_url, settings.icris_account,
        )
    if name == "sanctions" and settings.sanctions_api_url:
        return SanctionsProvider(settings.sanctions_api_url, settings.sanctions_api_key)
    return MockProvider()


def get_configured_providers() -> list:
    """按 .env 中已配置的 API_URL 实例化全部启用的 Provider。"""
    provs: list = []
    if settings.icris_api_url:
        provs.append(IcrisProvider(
            settings.icris_api_url, settings.icris_api_key,
            settings.icris_auth_url, settings.icris_account,
        ))
    if settings.sanctions_api_url:
        provs.append(SanctionsProvider(settings.sanctions_api_url, settings.sanctions_api_key))
    if settings.land_search_api_url:
        provs.append(LandRegistryProvider(settings.land_search_api_url, settings.land_search_api_key))
    if settings.credit_bureau_api_url:
        provs.append(CreditBureauProvider(
            settings.credit_bureau_api_url, settings.credit_bureau_api_key,
            settings.credit_bureau_member_id,
        ))
    if settings.ofac_api_url:
        provs.append(OfacProvider(settings.ofac_api_url, settings.ofac_api_key))
    if settings.hmt_api_url:
        provs.append(HmtProvider(settings.hmt_api_url, settings.hmt_api_key))
    if settings.crs_api_url:
        provs.append(CrsProvider(settings.crs_api_url, settings.crs_api_key))
    if settings.icij_api_url:
        provs.append(IcijProvider(settings.icij_api_url, settings.icij_api_key))
    if settings.opensanctions_api_url:
        provs.append(OpenSanctionsPepProvider(settings.opensanctions_api_url, settings.opensanctions_api_key))
    return provs


def enrich(vertical: str, extracted: dict, locale: str = "zh-HK",
           trace: Optional[list] = None) -> dict:
    """运行全部已配置的富集 Provider，与 mock 基线合并。

    当 .env 配置了对应 *_API_URL 时，对应 Provider 会被实际调用；
    任一外部源调用失败均自动降级并打「需人工複核」标记，流水线不中断。
    全部未配置时退化为 mock 基线（离线可跑）。
    """
    from app.trace import stamp

    result = _base_result(extracted, locale)
    providers = get_configured_providers()
    if not providers:
        return result
    result["provider"] = "+".join(p.name for p in providers)
    for p in providers:
        t0 = time.perf_counter()
        try:
            _merge(result, p.enrich(vertical, extracted, locale))
            stamp(trace, "enrich", getattr(p, "name", type(p).__name__), started=t0, ok=True,
                  configured=True)
        except Exception as e:  # 单个数据源异常不中断整条流水线
            stamp(trace, "enrich", getattr(p, "name", type(p).__name__), started=t0, ok=False, error=e,
                  configured=True)
    return result
