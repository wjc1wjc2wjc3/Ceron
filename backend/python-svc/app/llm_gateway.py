"""LLM 网关：统一封装抽取调用、prompt 管理与正则兜底，输出经 Schema 校验的对象。

对应架构中的 Python 智能服务层入口，供 Go 编排服务通过 REST 调用。
Prompt 明确支持 繁體中文 / 簡體中文 / English 混合文档（香港金融文档常见形态）。
"""
import json
from typing import Type

from pydantic import BaseModel

from typing import Optional

from app.llm import LLMClient
from app.llm_catalog import LLMCfg
from app.regex_extract import rule_extract

_CLIENT = LLMClient()

_SYSTEM = (
    "你是 Ceron 的香港金融文档抽取引擎，服务于港股保险、信托及家族办公室场景。"
    "文档可能为 繁體中文、簡體中文 或 English 混合，请统一理解后抽取。"
    "只输出 JSON，字段名使用中文（简体），金额统一换算为「万港币」数值，"
    "无法确定的字段填 null，不要输出解释。"
)


def _backfill_money(cleaned: dict, schema_cls: Type[BaseModel], candidates):
    if not candidates:
        return
    cands = list(candidates)
    for f in schema_cls.model_fields:
        if any(k in f for k in ("万", "金额", "保额", "保费", "资产规模")):
            if cleaned.get(f) is None and cands:
                cleaned[f] = cands.pop(0)


async def extract(text: str, schema_cls: Type[BaseModel], cfg: Optional[LLMCfg] = None,
                  trace: Optional[list] = None) -> BaseModel:
    """抽取结构化字段。传入 cfg 时使用该用户选定的模型，否则走服务级默认客户端。"""
    from app.trace import stamp

    hint = json.dumps(schema_cls.model_json_schema(), ensure_ascii=False)
    client = _CLIENT if cfg is None else LLMClient(cfg)
    raw = await client.extract(text, hint, trace=trace)

    if raw.get("_mock") or not raw:
        raw = rule_extract(text)
        stamp(trace, "extract", "rule_fallback", ok=True, model="regex", fallback=True)

    allowed = set(schema_cls.model_fields.keys())
    cleaned = {k: v for k, v in raw.items() if k in allowed}

    if "_金额候选" in raw:
        _backfill_money(cleaned, schema_cls, raw["_金额候选"])

    try:
        return schema_cls(**cleaned)
    except Exception:
        return schema_cls()
