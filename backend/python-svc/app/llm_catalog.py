"""大模型目录与「按用户」的模型配置解析。

平台用户可自主选择接入：DeepSeek / Kimi / GLM(智谱) / Qwen(通义) / Doubao(豆包)，
或新增**自定义模型**（OpenAI 兼容：模型名称 + base_url + api_key）。

密钥安全：设置保存后对外**只返回脱敏值**（如 `sk-a…3f9c`），完整密钥永不出网；
更新时若前端回传空串或脱敏值，则保留服务端已存密钥，避免误清空。
"""
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings

# 内置预设：base_url 与默认模型均可在使用时被覆盖（国产模型迭代快，留可编辑口）
PRESETS = [
    {"id": "deepseek", "label": "DeepSeek",
     "base_url": "https://api.deepseek.com/v1", "default_model": "deepseek-chat"},
    {"id": "kimi", "label": "Kimi (Moonshot)",
     "base_url": "https://api.moonshot.cn/v1", "default_model": "kimi-k3"},
    {"id": "glm", "label": "GLM (智谱)",
     "base_url": "https://open.bigmodel.cn/api/paas/v4", "default_model": "glm-4.6"},
    {"id": "qwen", "label": "Qwen (通义千问)",
     "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "default_model": "qwen-plus"},
    {"id": "doubao", "label": "Doubao (豆包)",
     "base_url": "https://ark.cn-beijing.volces.com/api/v3", "default_model": "doubao-pro-32k"},
]

PRESET_IDS = {p["id"] for p in PRESETS}
CUSTOM = "custom"


@dataclass
class LLMCfg:
    """一次抽取实际使用的模型配置。"""
    provider: str = "mock"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    json_mode: bool = True
    label: str = ""
    extra: dict = field(default_factory=dict)

    def usable(self) -> bool:
        return bool(self.api_key and self.base_url and self.model) and self.provider != "mock"


def preset(pid: str) -> Optional[dict]:
    return next((p for p in PRESETS if p["id"] == pid), None)


def mask_key(key: Optional[str]) -> str:
    """对外展示用脱敏密钥：仅保留前 4 与后 4 位。"""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}…{key[-4:]}"


def is_masked(value: Optional[str]) -> bool:
    """判断是否脱敏值（前端原样回传时应保留服务端密钥）。"""
    return (not value) or ("…" in value) or (value == "****")


def empty_config() -> dict:
    return {"active": "", "providers": {}, "customs": []}


def resolve(cfg: Optional[dict]) -> LLMCfg:
    """把用户保存的设置解析为可用配置；未配置时回落到服务级环境变量。"""
    cfg = cfg or {}
    active = cfg.get("active", "")
    customs = {c.get("id"): c for c in cfg.get("customs", [])}

    if active and active in customs:  # 自定义模型
        c = customs[active]
        return LLMCfg(
            provider=CUSTOM,
            base_url=(c.get("base_url") or "").rstrip("/"),
            model=c.get("model", ""),
            api_key=c.get("api_key", ""),
            json_mode=bool(c.get("json_mode", True)),
            label=c.get("name", "Custom model"),
            extra={"custom_id": c.get("id")},
        )

    p = preset(active)
    if p:  # 内置预设（用户可覆盖 base_url / model）
        over = (cfg.get("providers") or {}).get(active, {}) or {}
        return LLMCfg(
            provider=active,
            base_url=(over.get("base_url") or p["base_url"]).rstrip("/"),
            model=over.get("model") or p["default_model"],
            api_key=over.get("api_key", ""),
            label=p["label"],
        )

    # 未选择 / 未配置：回落到服务级环境变量（LLM_PROVIDER=mock 时零成本运行）
    return LLMCfg(
        provider=settings.llm_provider,
        base_url=settings.llm_base_url.rstrip("/"),
        model=settings.llm_model,
        api_key=settings.llm_api_key,
    )


def public_view(cfg: Optional[dict]) -> dict:
    """返回给前端的设置视图（密钥一律脱敏）。"""
    cfg = cfg or empty_config()
    providers = {}
    for pid, over in (cfg.get("providers") or {}).items():
        providers[pid] = {
            "base_url": over.get("base_url", ""),
            "model": over.get("model", ""),
            "api_key_masked": mask_key(over.get("api_key", "")),
            "has_key": bool(over.get("api_key")),
        }
    customs = [
        {
            "id": c.get("id"),
            "name": c.get("name", ""),
            "model": c.get("model", ""),
            "base_url": c.get("base_url", ""),
            "api_key_masked": mask_key(c.get("api_key", "")),
            "has_key": bool(c.get("api_key")),
            "json_mode": bool(c.get("json_mode", True)),
        }
        for c in cfg.get("customs", [])
    ]
    return {"active": cfg.get("active", ""), "providers": providers, "customs": customs}
