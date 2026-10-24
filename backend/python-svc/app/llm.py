"""LLM 客户端抽象层。

支持国产 / 国际大模型（DeepSeek / 通义 / 智谱 / OpenAI / Claude 等 OpenAI 兼容接口），
统一走 /chat/completions 并请求 JSON 输出。未配置密钥时回退到 mock，保证可零成本运行。
"""
import json

import httpx

from app.config import settings

SYSTEM_PROMPT = (
    "你是 Ceron 的中文金融文档抽取引擎，服务于中国的商业贷款、设备融资租赁与保险业务。"
    "请从用户提供的文档文本中提取结构化字段，只输出 JSON，字段名使用中文，"
    "无法确定的字段填空字符串或 null。不要输出任何解释性文字。"
)


class LLMClient:
    def __init__(self) -> None:
        self.provider = settings.llm_provider

    async def extract(self, text: str, schema_hint: str) -> dict:
        if self.provider == "mock" or not settings.llm_api_key:
            return {"_mock": True}

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n需要抽取的字段(JSON Schema 提示):\n" + schema_hint},
            {"role": "user", "content": text},
        ]
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
