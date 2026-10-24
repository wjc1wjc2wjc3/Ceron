"""OCR 抽象层：可插拔后端（mock / Azure Form Recognizer / Tesseract 繁中）。

港式银行月结单、保单扫描件等图片单据 → 文本，再交给 llm_gateway 抽取。
生产建议：Azure prebuilt-read（繁中+英）或自建 PaddleOCR 繁中服务（HTTP 对接）。
"""
import base64
import io
from typing import Protocol

from app.config import settings


class OcrProvider(Protocol):
    name: str

    async def recognize(self, image_base64: str) -> str: ...


class MockOcrProvider:
    """演示用：无真实 OCR 引擎时，把传入的 base64 当 UTF-8 文本还原。"""

    name = "mock"

    async def recognize(self, image_base64: str) -> str:
        try:
            return base64.b64decode(image_base64).decode("utf-8", errors="ignore")
        except Exception:
            return ""


class AzureFormRecognizerProvider:
    """Azure AI Document Intelligence（prebuilt-read）适配器骨架。"""

    name = "azure_form_recognizer"

    def __init__(self, endpoint: str, api_key: str, model: str = "prebuilt-read") -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def recognize(self, image_base64: str) -> str:
        import httpx  # 局部导入，未用时无需安装

        if not self.endpoint or not self.api_key:
            raise RuntimeError("缺少 AZURE_FORM_RECOGNIZER_ENDPOINT/KEY 配置")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.endpoint}/formrecognizer/documentModels/{self.model}:analyze"
                "?api-version=2023-07-31",
                headers={"Ocp-Apim-Subscription-Key": self.api_key,
                         "Content-Type": "application/octet-stream"},
                content=base64.b64decode(image_base64),
            )
            resp.raise_for_status()
            # analyze 返回 202 + Operation-Location，需轮询取结果
            poll_url = resp.headers.get("Operation-Location")
            if not poll_url:
                raise RuntimeError("Azure OCR 未返回 Operation-Location")
            import asyncio as _aio
            for _ in range(20):
                await _aio.sleep(1.5)
                poll = await client.get(poll_url, headers={"Ocp-Apim-Subscription-Key": self.api_key})
                poll.raise_for_status()
                data = poll.json()
                if data.get("status") in ("succeeded", "failed"):
                    break
            if data.get("status") != "succeeded":
                raise RuntimeError("Azure OCR 分析未成功")
            content = data["analyzeResult"]["content"]
            return content


class TesseractProvider:
    """本地 Tesseract（需安装 tesseract-ocr-chi-tra 语言包与 pytesseract）。"""

    name = "tesseract"

    async def recognize(self, image_base64: str) -> str:
        import asyncio

        def _run() -> str:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore

            img = Image.open(io.BytesIO(base64.b64decode(image_base64)))
            return pytesseract.image_to_string(img, lang="chi_tra+eng")

        return await asyncio.to_thread(_run)


def get_ocr_provider() -> OcrProvider:
    name = settings.ocr_provider
    if name == "azure":
        return AzureFormRecognizerProvider(settings.azure_form_endpoint, settings.azure_form_key)
    if name == "tesseract":
        return TesseractProvider()
    return MockOcrProvider()
