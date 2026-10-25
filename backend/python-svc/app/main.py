"""FastAPI 智能服务入口（Python 智能层）。

Go 编排服务（gateway/orchestrator）通过以下 REST 接口调用本服务：
  GET  /health
  POST /v1/extract   { vertical, text }
  POST /v1/ocr       { image_base64 }                  # OCR：扫描件/月结单 → 文本
  POST /v1/enrich    { vertical, extracted }
  POST /v1/decision  { vertical, extracted, enrichment }
  POST /v1/pipeline  { vertical, text | image_base64 } # 串联 OCR→抽取→富集→决策
"""
import json
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app import agent, auth, kb, llm, llm_catalog, mcp, rules
from app.kb import search as kb_search
from app.capabilities import snapshot as capabilities_snapshot
from app.compliance import check_data_residency
from app.config import settings
from app.decision import assess, assess_with_review
from app.enrichment import enrich
from app.extraction import extract_document
from app.mi import build_mi_report
from app.monitoring import run_scan, start_scheduler
from app.ocr import get_ocr_provider
from app.parsers import list_parsers, parse as parse_document
from app.sar import create_sar, list_sars, set_status
from app.schemas import Vertical
from app import store
from app.trace import new_trace, stamp, summary
from app.ubo import resolve as resolve_ubo

app = FastAPI(title="Ceron Intelligence Service", version="0.3.0",
              description="香港金融业承保与合规自动化的 Python 大模型智能服务层")


def require_roles(*allowed: str):
    """RBAC 依赖：要求登录且角色在允许集合内（空集合 = 只需登录）。

    涉及「改口径 / 对外申报」的写操作必须收敛到 reviewer / admin：
    规则休眠停用、告警处置、SAR 起草与流转——一旦被随意操作就是合规风险。

    定义在模块顶部：`Depends(require_roles(...))` 作为默认参数在**路由注册时**
    求值，晚于此处定义会导致 NameError。
    """

    def dep(authorization: Optional[str] = Header(None)) -> dict:
        payload = auth.verify_token(_token_from_header(authorization))
        if not payload:
            raise HTTPException(status_code=401, detail="auth_required")
        role = payload.get("role") or "analyst"
        if allowed and role not in allowed:
            raise HTTPException(status_code=403, detail=f"role_forbidden:{role}")
        return {"payload": payload, "role": role}

    return dep


class ExtractReq(BaseModel):
    # vertical 接受内置业务线或 schema 配置（SCHEMA_CONFIG）定义的任意自定义业务线
    vertical: str
    text: str


class OcrReq(BaseModel):
    image_base64: str


class EnrichReq(BaseModel):
    vertical: str
    extracted: dict


class DecisionReq(BaseModel):
    vertical: str
    extracted: dict
    enrichment: dict = {}
    locale: str = "zh-HK"


class PipelineReq(BaseModel):
    vertical: str
    text: str = ""
    image_base64: str = ""
    locale: str = "zh-HK"
    # 结构化股权边：[{"from":"A","to":"B","pct":60}]，供 UBO 图穿透使用（可选）
    ownership_edges: list = []


class ParseReq(BaseModel):
    file_base64: str
    filename: str = ""
    locale: str = "zh-HK"
    parser: Optional[str] = None


class SarReq(BaseModel):
    name: str
    vertical: str = ""
    reason: str = ""
    decision_summary: dict = {}


class AgentChatReq(BaseModel):
    """合规 Agent 一轮对话。session_id 留空则自动新建会话（多轮追问请带上）。"""
    message: str
    session_id: Optional[str] = None
    vertical: Optional[str] = None
    extracted: dict = {}
    locale: str = "zh-HK"


@app.on_event("startup")
def _startup() -> None:
    if settings.monitoring_enabled:
        start_scheduler(settings.monitoring_interval)


@app.get("/health")
def health():
    return {"status": "ok", "service": "intelligence", "compliance": check_data_residency()}


@app.post("/v1/ocr")
async def ocr_endpoint(req: OcrReq):
    provider = get_ocr_provider()
    text = await provider.recognize(req.image_base64)
    return {"ocr_provider": provider.name, "text": text}


@app.post("/v1/extract")
async def extract_endpoint(req: ExtractReq):
    return await extract_document(req.text, req.vertical)


@app.post("/v1/enrich")
def enrich_endpoint(req: EnrichReq):
    return {"vertical": req.vertical, "enrichment": enrich(req.vertical, req.extracted)}


@app.post("/v1/decision")
def decision_endpoint(req: DecisionReq):
    return {"vertical": req.vertical,
            "decision": assess(req.vertical, req.extracted, req.enrichment, req.locale)}


@app.post("/v1/pipeline")
async def pipeline_endpoint(req: PipelineReq, authorization: Optional[str] = Header(None)):
    text = req.text.strip()
    ocr_used = False
    if not text and req.image_base64:
        provider = get_ocr_provider()
        text = (await provider.recognize(req.image_base64)).strip()
        ocr_used = True
    if not text:
        return {"error": "text 或 image_base64 至少提供一项"}

    # 已登录用户按其选定的模型（内置预设 / 自定义）抽取；未登录则回落到服务级配置
    cfg = None
    payload = auth.verify_token(_token_from_header(authorization))
    if payload:
        cfg = llm_catalog.resolve(store.get_llm_config(payload.get("sub", "")))

    # 作业级 trace：记录每一步用的模型、数据源、耗时与成功与否（模型治理要求）
    trace = new_trace()
    res = await extract_document(text, req.vertical, cfg, trace=trace)
    enrichment = enrich(req.vertical, res["extracted"], req.locale, trace=trace)
    decision = assess_with_review(req.vertical, res["extracted"], enrichment, req.locale, trace=trace)

    # UBO 穿透（家办 / 信托 / 基金场景）：股权图相乘计算有效持股
    ubo = resolve_ubo(res["extracted"], req.ownership_edges)
    stamp(trace, "ubo", "graph", ok=not ubo.get("unresolved", True),
          mode=ubo.get("mode"), owners=len(ubo.get("beneficial_owners", [])))

    # 优先级 3：记录决策历史（供 MI）并登记实体（供持续监控）
    name = (
        res["extracted"].get("客户姓名或实体名称")
        or res["extracted"].get("投保人")
        or res["extracted"].get("申请人")
        or res["extracted"].get("成员姓名或实体名称")
        or res["extracted"].get("基金名称或实体名称")
        or res["extracted"].get("受保人")
    )
    run_id = store.record_run(
        req.vertical, decision["action"], decision["risk_score"], name,
        extra={
            "locale": req.locale,
            "ocr_used": ocr_used,
            "extracted": res["extracted"],
            "masked_source_preview": res["masked_source_preview"],
            "enrichment": enrichment,
            "decision": decision,
            "ubo": ubo,
            "trace": trace,
        },
    )
    return {
        "vertical": res["vertical"],
        "run_id": run_id,
        "ocr_used": ocr_used,
        "extracted": res["extracted"],
        "masked_source_preview": res["masked_source_preview"],
        "enrichment": enrichment,
        "decision": decision,
        "ubo": ubo,
        "trace": trace,
        "trace_summary": summary(trace),
    }


# ============ 优先级 3：持续监控 / SAR 申报 / 监管 MI ============

@app.post("/v1/monitoring/scan")
def monitoring_scan():
    """触发对已登记实体的 sanctions/OFAC/HMT 重查，返回命中实体名。"""
    hits = run_scan()
    return {"scanned": len(store.list_entities()), "hits": hits}


@app.get("/v1/monitoring/alerts")
def monitoring_alerts():
    return {"alerts": store.list_alerts()}


@app.patch("/v1/monitoring/alerts/{alert_id}")
def monitoring_alert_status(alert_id: str, body: dict,
                            who: dict = Depends(require_roles("reviewer", "admin"))):
    """告警处置：open → acknowledged（已认领）→ resolved（已结案）。"""
    status = body.get("status")
    if status not in ("open", "acknowledged", "resolved"):
        raise HTTPException(status_code=400, detail="invalid status")
    updated = store.update_alert(alert_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="alert not found")
    return updated


@app.post("/v1/monitoring/alerts/{alert_id}/sar")
def monitoring_alert_to_sar(alert_id: str,
                            who: dict = Depends(require_roles("reviewer", "admin"))):
    """从告警一键起草 SAR：把「发现 → 申报」两步串成一跳，避免人工漏报。"""
    alert = None
    for a in store.list_alerts():
        if str(a.get("id")) == str(alert_id):
            alert = a
            break
    if not alert:
        raise HTTPException(status_code=404, detail="alert not found")
    sar = create_sar(
        alert.get("name", ""), alert.get("vertical", ""),
        f"{alert.get('reason','')}（名单：{(alert.get('lists') or []) }）",
        {"source": "monitoring_alert", "alert_id": str(alert_id)},
    )
    store.update_alert(alert_id, "acknowledged")
    return sar


@app.post("/v1/sar")
def sar_create(req: SarReq, who: dict = Depends(require_roles("reviewer", "admin"))):
    """创建一份 SAR 草稿（高风险决策应触发 SAR 申报评估）。"""
    sar = create_sar(req.name, req.vertical, req.reason, req.decision_summary)
    return {"sar": sar}


@app.get("/v1/sar")
def sar_list():
    return {"sars": list_sars()}


@app.post("/v1/sar/{sar_id}/status")
def sar_status(sar_id: str, body: dict,
               who: dict = Depends(require_roles("reviewer", "admin"))):
    updated = set_status(sar_id, body.get("status", "submitted"))
    if not updated:
        raise HTTPException(status_code=404, detail="sar not found")
    return {"sar": updated}


@app.get("/v1/mi")
def mi_report():
    """监管 MI 报表：决策统计、告警与 SAR 汇总。"""
    return build_mi_report()


# ============ 能力覆盖度 / 规则包 / 审计包 / 解析器 / MCP ============

@app.get("/v1/capabilities")
def capabilities(locale: str = "zh-HK"):
    """对外可引用的覆盖度数字：业务线、数据源、闸口规则、模型预设、解析器。"""
    return capabilities_snapshot(locale)


@app.get("/v1/rules")
def rules_export(version: Optional[str] = None, vertical: Optional[str] = None):
    """导出合规闸口规则包（可 diff / 可交给合规审阅）；按 vertical 过滤。"""
    pack = rules.export(version)
    if vertical:
        pack["rules"] = [r for r in pack["rules"] if r["vertical"] in ("*", vertical)]
        pack["count"] = len(pack["rules"])
    return pack


@app.get("/v1/rules/version")
def rules_version():
    return {"version": rules.RULE_PACK_VERSION, "count": len(rules.RULES)}


@app.post("/v1/rules/{rule_id}/state")
def rules_state(rule_id: str, body: dict,
                who: dict = Depends(require_roles("reviewer", "admin"))):
    """规则运行期治理（借鉴 marble 的 rule snooze）：

    - ``enabled: false`` 停用（误报止血，免发版）；
    - ``snoozed_until``: ISO 时间戳，休眠到指定时刻（数据源维护窗口等）；
    - 传 ``enabled: true`` / ``snoozed_until: ""`` 恢复。
    重启后恢复规则包原始状态（规则内容本身仍在代码里版本化）。
    """
    state = rules.set_rule_state(
        rule_id,
        enabled=body.get("enabled"),
        snoozed_until=body.get("snoozed_until"),
    )
    if state is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return {"rule_id": rule_id, "state": state}


@app.get("/v1/runs/{run_id}/audit")
def run_audit(run_id: str):
    """审计包：一次作业的完整证据链（抽取字段 / 富集信号 / 规则命中 / 决策 / trace / UBO）。"""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    decision = run.get("decision") or {}
    return {
        "run_id": run.get("id", run_id),
        "ts": run.get("ts"),
        "vertical": run.get("vertical"),
        "locale": run.get("locale", "zh-HK"),
        "generated_at": store.now_iso(),
        "schema_version": "ceron-audit-1.0",
        "rule_pack": decision.get("rule_pack") or {"version": rules.RULE_PACK_VERSION},
        "subject": run.get("name"),
        "extracted": run.get("extracted", {}),
        "masked_source_preview": run.get("masked_source_preview", ""),
        "enrichment": run.get("enrichment", {}),
        "decision": decision,
        "evidence": decision.get("evidence", []),
        "ubo": run.get("ubo"),
        "review": decision.get("review"),
        "trace": run.get("trace", []),
        "trace_summary": summary(run.get("trace", [])),
    }


@app.post("/v1/kb/search")
def kb_search_endpoint(body: dict):
    """法规速检：检索可引用的监管依据（内部摘要，非官方法规原文）。"""
    return {
        "query": body.get("query", ""),
        "clauses": kb_search(body.get("query", ""), top_k=int(body.get("top_k") or 5),
                             vertical=body.get("vertical"), gate=body.get("gate")),
    }


@app.post("/v1/agent/chat")
async def agent_chat_endpoint(req: AgentChatReq):
    """合规 Agent 对话：规划 → 工具调用 → 反思，返回带监管引用与工具轨迹的回答。"""
    trace = new_trace()
    out = await agent.chat(
        req.message, session_id=req.session_id, vertical=req.vertical,
        extracted=req.extracted, locale=req.locale, trace=trace,
    )
    return out


@app.get("/v1/agent/session/{session_id}")
def agent_session(session_id: str):
    """查看多轮会话记忆（Audit 要求：Agent 说过的话必须可回溯）。"""
    hist = agent.get_session(session_id)
    if hist is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "messages": hist}


@app.delete("/v1/agent/session/{session_id}")
def agent_session_delete(session_id: str):
    if not agent.delete_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return {"ok": True}


@app.get("/v1/parsers")
def parsers_list(locale: str = "zh-HK"):
    """已注册的文档解析器与可用性（PaddleOCR / Docling / Marker / 内置）。"""
    return list_parsers(locale)


@app.post("/v1/parse")
def parse_endpoint(req: ParseReq):
    """单文件解析（可插拔解析器，不可用自动降级内置）。"""
    import base64

    trace = new_trace()
    data = base64.b64decode(req.file_base64 or "")
    out = parse_document(data, req.filename, req.locale, req.parser, trace=trace)
    out["trace"] = trace
    return out


@app.get("/v1/mcp/tools")
def mcp_tools():
    """MCP 工具清单：把抽取/富集/决策/UBO/规则包暴露给任意 Agent 调用。"""
    return {"tools": mcp.tools_list(), "protocol": "mcp-jsonrpc-2.0"}


@app.post("/v1/mcp")
async def mcp_rpc(body: dict):
    """最小 JSON-RPC 2.0 入口（methods: tools/list、tools/call）。"""
    return await mcp.handle_rpc(body)


@app.post("/v1/ubo")
def ubo_endpoint(body: dict):
    """UBO 图穿透：股权边相乘计算有效持股，识别循环持股与未穿透情形。"""
    return resolve_ubo(body.get("extracted", {}), body.get("ownership_edges"), body.get("root"))


# ============ 认证（Auth）：注册 / 登录 / 会话 / X / Facebook 第三方登录 ============

class RegisterReq(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginReq(BaseModel):
    email: str
    password: str


class EmailCodeReq(BaseModel):
    email: str
    purpose: str = "login"


class VerifyCodeReq(BaseModel):
    email: str
    code: str
    name: str = ""


class ForgotReq(BaseModel):
    email: str


class ResetReq(BaseModel):
    token: str
    new_password: str


def _token_from_header(authorization: Optional[str]) -> Optional[str]:
    """接受 `Bearer <token>` 或裸 token 两种写法。"""
    if not authorization:
        return None
    parts = authorization.split()
    return parts[-1] if len(parts) in (1, 2) else None


@app.get("/v1/auth/providers")
def auth_providers():
    """前端据此决定是否显示「使用 X / Facebook 登录」按钮。"""
    return {"providers": auth.configured_providers()}


@app.post("/v1/auth/register")
def auth_register(req: RegisterReq):
    try:
        user = auth.register(req.email, req.password, req.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return auth.issue(user)


@app.post("/v1/auth/login")
def auth_login(req: LoginReq):
    user = auth.login(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return auth.issue(user)


@app.get("/v1/auth/me")
def auth_me(authorization: Optional[str] = Header(None)):
    payload = auth.verify_token(_token_from_header(authorization))
    if not payload:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = store.get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"user": auth.public_user(user)}


@app.post("/v1/auth/logout")
def auth_logout():
    """无状态 JWT：服务端无需处理，客户端丢弃令牌即可。"""
    return {"ok": True}


@app.post("/v1/auth/email/code")
def auth_email_code(req: EmailCodeReq):
    """邮箱验证码：向邮箱发送 6 位验证码（未注册等同注册，验证码登录即账号开通）。"""
    try:
        wait, echo = auth.request_email_code(req.email, req.purpose)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    body = {"sent": True, "resend_wait": wait}
    if echo:  # 开发环境回显，生产（配置了 SMTP）不会返回
        body["dev_code"] = echo
    return body


@app.post("/v1/auth/email/verify")
def auth_email_verify(req: VerifyCodeReq):
    try:
        user = auth.verify_email_code(req.email, req.code, req.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return auth.issue(user)


@app.post("/v1/auth/password/forgot")
def auth_password_forgot(req: ForgotReq):
    """发起密码重置。无论邮箱是否存在都返回成功，避免账号枚举。"""
    echo = auth.start_password_reset(req.email)
    body = {"ok": True}
    if echo:
        body["dev_link"] = echo
    return body


# ============ 大模型（LLM）设置：用户自主选择 / 自定义模型 ============

class LlmSettingsReq(BaseModel):
    active: str = ""
    providers: dict = {}
    customs: list = []


class LlmCustomReq(BaseModel):
    name: str
    model: str
    base_url: str
    api_key: str = ""
    json_mode: bool = True


class LlmTestReq(BaseModel):
    provider: str = ""          # 内置预设 id
    custom_id: str = ""         # 自定义模型 id
    base_url: str = ""
    model: str = ""
    api_key: str = ""


def _current_user(authorization: Optional[str]) -> dict:
    """解析当前登录用户（模型设置属于用户私有数据，必须鉴权）。"""
    payload = auth.verify_token(_token_from_header(authorization))
    if not payload:
        raise HTTPException(status_code=401, detail="unauthorized")
    user = store.get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    return user


def _save_llm(user_id: str, incoming: dict) -> dict:
    """保存设置；空/脱敏密钥保留服务端原值，避免误清空。"""
    old = store.get_llm_config(user_id) or llm_catalog.empty_config()
    providers = dict(old.get("providers") or {})
    for pid, over in (incoming.get("providers") or {}).items():
        cur = dict(providers.get(pid) or {})
        for k in ("base_url", "model"):
            if over.get(k):
                cur[k] = over[k]
        if not llm_catalog.is_masked(over.get("api_key")):
            cur["api_key"] = over["api_key"]
        providers[pid] = cur

    old_customs = {c.get("id"): dict(c) for c in (old.get("customs") or [])}
    for c in incoming.get("customs") or []:
        cid = c.get("id")
        if not cid or cid not in old_customs:
            continue
        cur = old_customs[cid]
        for k in ("name", "model", "base_url"):
            if c.get(k):
                cur[k] = c[k]
        cur["json_mode"] = bool(c.get("json_mode", True))
        if not llm_catalog.is_masked(c.get("api_key")):
            cur["api_key"] = c.get("api_key", "")

    cfg = {
        "active": incoming.get("active", old.get("active", "")),
        "providers": providers,
        "customs": list(old_customs.values()),
    }
    store.set_llm_config(user_id, cfg)
    return cfg


@app.get("/v1/llm/presets")
def llm_presets():
    """内置模型目录 + 自定义入口（无需登录，便于前端渲染选择卡片）。"""
    return {
        "presets": llm_catalog.PRESETS,
        "custom": {"id": llm_catalog.CUSTOM, "label": "Custom model (OpenAI-compatible)"},
    }


@app.get("/v1/llm/settings")
def llm_get_settings(authorization: Optional[str] = Header(None)):
    user = _current_user(authorization)
    cfg = store.get_llm_config(user["id"])
    return {"settings": llm_catalog.public_view(cfg)}


@app.put("/v1/llm/settings")
def llm_put_settings(req: LlmSettingsReq, authorization: Optional[str] = Header(None)):
    user = _current_user(authorization)
    active = req.active
    known = llm_catalog.PRESET_IDS | {
        c.get("id") for c in (store.get_llm_config(user["id"]) or {}).get("customs", [])
    }
    if active and active not in known:
        raise HTTPException(status_code=400, detail="unknown_provider")
    cfg = _save_llm(user["id"], req.model_dump())
    return {"settings": llm_catalog.public_view(cfg)}


@app.post("/v1/llm/custom")
def llm_add_custom(req: LlmCustomReq, authorization: Optional[str] = Header(None)):
    """新增自定义模型（OpenAI 兼容：名称 + base_url + api_key + 模型名）。"""
    user = _current_user(authorization)
    if not req.base_url.strip() or not req.model.strip():
        raise HTTPException(status_code=400, detail="base_url_and_model_required")
    cfg = store.get_llm_config(user["id"]) or llm_catalog.empty_config()
    customs = cfg.get("customs") or []
    item = {
        "id": f"cm-{uuid.uuid4().hex[:10]}",
        "name": req.name or req.model,
        "model": req.model,
        "base_url": req.base_url.rstrip("/"),
        "api_key": req.api_key,
        "json_mode": bool(req.json_mode),
    }
    customs.append(item)
    cfg["customs"] = customs
    cfg["active"] = cfg.get("active") or item["id"]  # 首个自定义模型默认启用
    store.set_llm_config(user["id"], cfg)
    return {"custom": llm_catalog.public_view(cfg)["customs"][-1]}


@app.delete("/v1/llm/custom/{custom_id}")
def llm_delete_custom(custom_id: str, authorization: Optional[str] = Header(None)):
    user = _current_user(authorization)
    cfg = store.get_llm_config(user["id"]) or llm_catalog.empty_config()
    cfg["customs"] = [c for c in (cfg.get("customs") or []) if c.get("id") != custom_id]
    if cfg.get("active") == custom_id:
        cfg["active"] = ""
    store.set_llm_config(user["id"], cfg)
    return {"ok": True}


@app.post("/v1/llm/test")
async def llm_test(req: LlmTestReq, authorization: Optional[str] = Header(None)):
    """连通性测试：真实发一次极短对话，验证 base_url / 模型 / 密钥是否正确。"""
    _current_user(authorization)
    cfg = llm_catalog.resolve({
        "active": req.custom_id or req.provider,
        "customs": ([{"id": req.custom_id, "base_url": req.base_url, "model": req.model,
                      "api_key": req.api_key, "json_mode": True}] if req.custom_id else []),
        "providers": ({req.provider: {"base_url": req.base_url, "model": req.model,
                                      "api_key": req.api_key}} if req.provider else {}),
    })
    if not cfg.usable():
        return {"ok": False, "error": "missing_base_url_model_or_key"}
    try:
        client = llm.LLMClient(cfg)
        await client.extract("ping", json.dumps({"ping": "string"}, ensure_ascii=False))
        return {"ok": True, "provider": cfg.provider, "model": cfg.model}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


@app.post("/v1/auth/password/reset")
def auth_password_reset(req: ResetReq):
    try:
        done = auth.complete_password_reset(req.token, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not done:
        raise HTTPException(status_code=400, detail="token_invalid_or_expired")
    return {"ok": True}


@app.get("/v1/auth/x/authorize")
def auth_x_authorize():
    url = auth.x_authorize()
    if not url:
        raise HTTPException(status_code=503, detail="x_not_configured")
    return {"authorization_url": url}


@app.get("/v1/auth/x/callback")
async def auth_x_callback(request: Request):
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    target = settings.frontend_url.rstrip("/")
    try:
        user = await auth.x_callback(code, state)
    except Exception as e:
        return RedirectResponse(f"{target}/login?error={e}")
    return RedirectResponse(f"{target}/auth/callback?token={auth.create_token(user)}")


@app.get("/v1/auth/facebook/authorize")
def auth_facebook_authorize():
    url = auth.facebook_authorize()
    if not url:
        raise HTTPException(status_code=503, detail="facebook_not_configured")
    return {"authorization_url": url}


@app.get("/v1/auth/facebook/callback")
async def auth_facebook_callback(request: Request):
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    target = settings.frontend_url.rstrip("/")
    try:
        user = await auth.facebook_callback(code, state)
    except Exception as e:
        return RedirectResponse(f"{target}/login?error={e}")
    return RedirectResponse(f"{target}/auth/callback?token={auth.create_token(user)}")
