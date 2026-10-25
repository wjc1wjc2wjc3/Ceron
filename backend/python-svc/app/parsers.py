"""文档解析层（Parser）：把「文件 → 文本/版面」做成像富集数据源一样的**可插拔 Provider**。

为什么要抽这一层：
- 香港承保场景的输入极不统一（繁中保单附表、英文医疗报告、简体资产证明、手机拍照件、
  带表格与印章的 PDF），单一 OCR 方案必然有短板；
- 开源 SOTA 迭代很快（PaddleOCR / Docling / Marker 各自强项不同），硬绑定会锁死升级路径。

因此这里按「Provider 注册表 + 可用性探测 + 失败降级」的同样范式组织，
未安装依赖时自动不可用，绝不因为解析器缺失而中断流水线。
"""
from typing import Optional, Protocol
import importlib.util

from app.config import settings

_TR = {
    "zh-HK": {
        "not_installed": "{name} 未安装（pip install {pip}），已降级。",
        "ok": "{name} 解析完成。",
        "internal": "内置解析器（正则/文本）",
        "paddleocr": "PaddleOCR（中文/繁体最强开源 OCR 之一）",
        "docling": "Docling（IBM，MIT 许可，版面/表格/公式）",
        "marker": "Marker（PDF → Markdown，注意商用授权）",
    },
    "en": {
        "not_installed": "{name} not installed (pip install {pip}); falling back.",
        "ok": "{name} parsing complete.",
        "internal": "Internal parser (regex/text)",
        "paddleocr": "PaddleOCR (strong open-source Chinese OCR)",
        "docling": "Docling (IBM, MIT, layout/table/formula)",
        "marker": "Marker (PDF to Markdown; check commercial licence)",
    },
    "zh-CN": {
        "not_installed": "{name} 未安装（pip install {pip}），已降级。",
        "ok": "{name} 解析完成。",
        "internal": "内置解析器（正则/文本）",
        "paddleocr": "PaddleOCR（中文/繁体最强开源 OCR 之一）",
        "docling": "Docling（IBM，MIT 许可，版面/表格/公式）",
        "marker": "Marker（PDF → Markdown，注意商用授权）",
    },
}


def _t(locale: str, key: str, **vars) -> str:
    tpl = (_TR.get(locale) or _TR["zh-HK"]).get(key, key)
    try:
        return tpl.format(**vars)
    except (KeyError, IndexError):
        return tpl


def _installed(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


class ParserProvider(Protocol):
    id: str
    pip: str

    def available(self) -> bool: ...
    def parse(self, data: bytes, filename: str = "", locale: str = "zh-HK") -> dict: ...


class InternalParser:
    """零依赖内置解析器：直接按文本处理（PDF 走轻量抽取，图片则标记为需 OCR）。"""

    id = "internal"
    pip = ""

    def available(self) -> bool:
        return True

    def parse(self, data: bytes, filename: str = "", locale: str = "zh-HK") -> dict:
        name = (filename or "").lower()
        text = ""
        if name.endswith((".txt", ".md", ".csv", ".json")) or not name:
            text = data.decode("utf-8", errors="ignore")
        elif name.endswith(".pdf"):
            text = _pdf_text(data)
        return {
            "parser": self.id,
            "text": text,
            "needs_ocr": name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tiff")) or (name.endswith(".pdf") and not text),
            "note": _t(locale, "internal"),
        }


class PaddleOcrParser:
    """PaddleOCR：中文/繁体场景最强开源 OCR 之一（需 pip install paddleocr）。"""

    id = "paddleocr"
    pip = "paddleocr"

    def available(self) -> bool:
        return _installed("paddleocr")

    def parse(self, data: bytes, filename: str = "", locale: str = "zh-HK") -> dict:
        from paddleocr import PaddleOCR  # 延迟导入

        engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        result = engine.ocr(data, cls=True)
        lines = []
        for page in (result or []):
            for line in page or []:
                if line and len(line) >= 2:
                    lines.append(str(line[1][0]))
        return {
            "parser": self.id,
            "text": "\n".join(lines),
            "needs_ocr": False,
            "lines": len(lines),
            "note": _t(locale, "paddleocr"),
        }


class DoclingParser:
    """Docling（MIT）：版面/表格/公式解析；支持本地库或 docling-serve HTTP 端点。"""

    id = "docling"
    pip = "docling"

    def __init__(self, api_url: str = "") -> None:
        self.api_url = api_url

    def available(self) -> bool:
        return bool(self.api_url) or _installed("docling")

    def parse(self, data: bytes, filename: str = "", locale: str = "zh-HK") -> dict:
        if self.api_url:
            import httpx

            resp = httpx.post(
                self.api_url.rstrip("/") + "/v1/convert/file",
                files={"files": (filename or "doc.pdf", data)},
                timeout=120.0,
            )
            resp.raise_for_status()
            body = resp.json()
            doc = (body.get("document") or {})
            return {
                "parser": self.id,
                "text": doc.get("md_content") or doc.get("text") or "",
                "needs_ocr": False,
                "mode": "docling-serve",
                "note": _t(locale, "docling"),
            }
        from docling.document_converter import DocumentConverter  # 延迟导入
        import tempfile, os

        suffix = os.path.splitext(filename or "doc.pdf")[1] or ".pdf"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            conv = DocumentConverter().convert(path)
            return {
                "parser": self.id,
                "text": conv.document.export_to_markdown(),
                "needs_ocr": False,
                "mode": "local",
                "note": _t(locale, "docling"),
            }
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


class MarkerParser:
    """Marker：PDF → Markdown（注意：模型权重的商用授权限制）。"""

    id = "marker"
    pip = "marker-pdf"

    def available(self) -> bool:
        return _installed("marker")

    def parse(self, data: bytes, filename: str = "", locale: str = "zh-HK") -> dict:
        from marker.converters.pdf import PdfConverter  # 延迟导入（示例契约）
        from marker.models import create_model_dict
        import tempfile, os

        suffix = os.path.splitext(filename or "doc.pdf")[1] or ".pdf"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            converter = PdfConverter(artifact_dict=create_model_dict())
            rendered = converter(path)
            return {
                "parser": self.id,
                "text": getattr(rendered, "markdown", "") or "",
                "needs_ocr": False,
                "note": _t(locale, "marker"),
            }
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


def _pdf_text(data: bytes) -> str:
    """轻量 PDF 文本抽取（pypdf 可用时用之，否则空串 → 标记需 OCR）。"""
    if not _installed("pypdf"):
        return ""
    try:
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:20])
    except Exception:
        return ""


def _registry() -> list:
    return [
        PaddleOcrParser(),
        DoclingParser(getattr(settings, "docling_api_url", "") or ""),
        MarkerParser(),
        InternalParser(),  # 永远可用，放最后作为兜底
    ]


def list_parsers(locale: str = "zh-HK") -> dict:
    active = getattr(settings, "parser_provider", "internal") or "internal"
    items = []
    for p in _registry():
        try:
            ok = bool(p.available())
        except Exception:
            ok = False
        items.append({
            "id": p.id,
            "available": ok,
            "active": p.id == active,
            "install": p.pip,
            "note": _t(locale, p.id) if p.id in _TR["zh-HK"] else p.id,
        })
    return {"active": active, "parsers": items}


def parse(data: bytes, filename: str = "", locale: str = "zh-HK",
          provider: Optional[str] = None, trace: Optional[list] = None) -> dict:
    """按配置的解析器解析文件；不可用或失败时降级到内置解析器（并记录 trace）。"""
    from app.trace import stamp
    import time

    wanted = provider or getattr(settings, "parser_provider", "internal") or "internal"
    for p in _registry():
        if p.id != wanted:
            continue
        try:
            if not p.available():
                stamp(trace, "parse", p.id, ok=False, error=_t(locale, "not_installed", name=p.id, pip=p.pip or "-"))
                break
            t0 = time.perf_counter()
            out = p.parse(data, filename, locale)
            stamp(trace, "parse", p.id, started=t0, ok=True, bytes=len(data or b""))
            return out
        except Exception as e:
            stamp(trace, "parse", p.id, ok=False, error=e)
            break

    t0 = time.perf_counter()
    out = InternalParser().parse(data, filename, locale)
    stamp(trace, "parse", InternalParser.id, started=t0, ok=True, fallback=True, bytes=len(data or b""))
    out["fallback"] = True
    return out
