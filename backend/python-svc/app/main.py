"""FastAPI 智能服务入口（Python 智能层）。

Go 编排服务（gateway/orchestrator）通过以下 REST 接口调用本服务：
  GET  /health
  POST /v1/extract   { vertical, text }
  POST /v1/ocr       { image_base64 }                  # OCR：扫描件/月结单 → 文本
  POST /v1/enrich    { vertical, extracted }
  POST /v1/decision  { vertical, extracted, enrichment }
  POST /v1/pipeline  { vertical, text | image_base64 } # 串联 OCR→抽取→富集→决策
"""
from fastapi import FastAPI
from pydantic import BaseModel

from app.compliance import check_data_residency
from app.decision import assess
from app.enrichment import enrich
from app.extraction import extract_document
from app.ocr import get_ocr_provider
from app.schemas import Vertical

app = FastAPI(title="Ceron Intelligence Service", version="0.3.0",
              description="Heron 产品的香港金融业本土化：Python 大模型智能服务层")


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


class PipelineReq(BaseModel):
    vertical: Vertical
    text: str = ""
    image_base64: str = ""


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
            "decision": assess(req.vertical, req.extracted, req.enrichment)}


@app.post("/v1/pipeline")
async def pipeline_endpoint(req: PipelineReq):
    text = req.text.strip()
    ocr_used = False
    if not text and req.image_base64:
        provider = get_ocr_provider()
        text = (await provider.recognize(req.image_base64)).strip()
        ocr_used = True
    if not text:
        return {"error": "text 或 image_base64 至少提供一项"}

    res = await extract_document(text, req.vertical)
    enrichment = enrich(req.vertical.value, res["extracted"])
    decision = assess(req.vertical, res["extracted"], enrichment)
    return {
        "vertical": res["vertical"],
        "ocr_used": ocr_used,
        "extracted": res["extracted"],
        "masked_source_preview": res["masked_source_preview"],
        "enrichment": enrichment,
        "decision": decision,
    }
