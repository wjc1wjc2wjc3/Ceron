"""LLM 客户端抽象层。

支持国产 / 国际大模型（DeepSeek / 通义 / 智谱 / OpenAI / Claude 等 OpenAI 兼容接口），
统一走 /chat/completions 并请求 JSON 输出。未配置密钥时回退到 mock，保证可零成本运行。
"""
import json
from typing import Optional

import httpx

from app.config import settings
from app.llm_catalog import LLMCfg

SYSTEM_PROMPT = (
    "你是 Ceron 的中文金融文档抽取引擎，服务于中国的商业贷款、设备融资租赁与保险业务。"
    "请从用户提供的文档文本中提取结构化字段，只输出 JSON，字段名使用中文，"
    "无法确定的字段填空字符串或 null。不要输出任何解释性文字。"
)


class LLMClient:
    """抽取用大模型客户端。

    传入 ``cfg``（来自用户设置：内置预设或自定义模型）时按用户配置调用；
    未传入时回落到服务级环境变量（LLM_PROVIDER=mock 即零成本运行）。
    """

    def __init__(self, cfg: Optional[LLMCfg] = None) -> None:
        self.cfg = cfg
        self.provider = cfg.provider if cfg else settings.llm_provider

    @property
    def base_url(self) -> str:
        return (self.cfg.base_url if self.cfg else settings.llm_base_url).rstrip("/")

    @property
    def model(self) -> str:
        return self.cfg.model if self.cfg else settings.llm_model

    @property
    def api_key(self) -> str:
        return self.cfg.api_key if self.cfg else settings.llm_api_key

    @property
    def json_mode(self) -> bool:
        return self.cfg.json_mode if self.cfg else True

    async def extract(self, text: str, schema_hint: str) -> dict:
        if self.provider == "mock" or not self.api_key:
            return {"_mock": True}

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n需要抽取的字段(JSON Schema 提示):\n" + schema_hint},
            {"role": "user", "content": text},
        ]
        payload = {"model": self.model, "messages": messages}
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            # 部分国产模型不支持 response_format：400 时降级重试一次
            if resp.status_code == 400 and self.json_mode:
                payload.pop("response_format", None)
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
