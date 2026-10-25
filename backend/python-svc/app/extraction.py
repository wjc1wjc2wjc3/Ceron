"""文档抽取流水线：调用 LLM 网关，回退到中文正则规则。"""
from typing import Optional

from app.compliance import mask_pii
from app.llm_catalog import LLMCfg
from app.llm_gateway import extract
from app.schemas import Vertical, get_schema


async def extract_document(text: str, vertical: Vertical,
                           cfg: Optional[LLMCfg] = None,
                           trace: Optional[list] = None) -> dict:
    schema_cls = get_schema(vertical)
    model = await extract(text, schema_cls, cfg, trace=trace)
    payload = model.model_dump(exclude_none=True)
    return {
        "vertical": vertical.value,
        "extracted": payload,
        "masked_source_preview": mask_pii(text)[:160],
    }
