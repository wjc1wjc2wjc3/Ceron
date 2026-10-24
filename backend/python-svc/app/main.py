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

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app import auth, llm, llm_catalog
from app.compliance import check_data_residency
from app.config import settings
from app.decision import assess
from app.enrichment import enrich
from app.extraction import extract_document
from app.mi import build_mi_report
from app.monitoring import run_scan, start_scheduler
from app.ocr import get_ocr_provider
from app.sar import create_sar, list_sars, set_status
from app.schemas import Vertical
from app import store

app = FastAPI(title="Ceron Intelligence Service", version="0.3.0",
              description="香港金融业承保与合规自动化的 Python 大模型智能服务层")


class ExtractReq(BaseModel):
    vertical: Vertical
    text: str


class OcrReq(BaseModel):
    image_base64: str


class EnrichReq(BaseModel):
    vertical: Vertical
    extracted: dict


class DecisionReq(BaseModel):
    vertical: Vertical
    extracted: dict
    enrichment: dict = {}
    locale: str = "zh-HK"


class PipelineReq(BaseModel):
    vertical: Vertical
    text: str = ""
    image_base64: str = ""
    locale: str = "zh-HK"


class SarReq(BaseModel):
    name: str
    vertical: str = ""
    reason: str = ""
    decision_summary: dict = {}


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
    return {"vertical": req.vertical.value, "enrichment": enrich(req.vertical.value, req.extracted)}


@app.post("/v1/decision")
def decision_endpoint(req: DecisionReq):
    return {"vertical": req.vertical.value,
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
    res = await extract_document(text, req.vertical, cfg)
    enrichment = enrich(req.vertical.value, res["extracted"], req.locale)
    decision = assess(req.vertical, res["extracted"], enrichment, req.locale)
    # 优先级 3：记录决策历史（供 MI）并登记实体（供持续监控）
    name = (
        res["extracted"].get("客户姓名或实体名称")
        or res["extracted"].get("投保人")
        or res["extracted"].get("申请人")
        or res["extracted"].get("成员姓名或实体名称")
        or res["extracted"].get("基金名称或实体名称")
        or res["extracted"].get("受保人")
    )
    store.record_run(req.vertical.value, decision["action"], decision["risk_score"], name)
    return {
        "vertical": res["vertical"],
        "ocr_used": ocr_used,
        "extracted": res["extracted"],
        "masked_source_preview": res["masked_source_preview"],
        "enrichment": enrichment,
        "decision": decision,
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


@app.post("/v1/sar")
def sar_create(req: SarReq):
    """创建一份 SAR 草稿（高风险决策应触发 SAR 申报评估）。"""
    sar = create_sar(req.name, req.vertical, req.reason, req.decision_summary)
    return {"sar": sar}


@app.get("/v1/sar")
def sar_list():
    return {"sars": list_sars()}


@app.post("/v1/sar/{sar_id}/status")
def sar_status(sar_id: str, body: dict):
    updated = set_status(sar_id, body.get("status", "submitted"))
    if not updated:
        raise HTTPException(status_code=404, detail="sar not found")
    return {"sar": updated}


@app.get("/v1/mi")
def mi_report():
    """监管 MI 报表：决策统计、告警与 SAR 汇总。"""
    return build_mi_report()


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
