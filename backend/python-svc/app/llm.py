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

    async def extract(self, text: str, schema_hint: str, trace: Optional[list] = None) -> dict:
        import time

        from app.trace import stamp

        if self.provider == "mock" or not self.api_key:
            stamp(trace, "extract", self.provider or "mock", started=time.perf_counter(), ok=True,
                  model=self.model, fallback=True)
            return {"_mock": True}

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n需要抽取的字段(JSON Schema 提示):\n" + schema_hint},
            {"role": "user", "content": text},
        ]
        payload = {"model": self.model, "messages": messages}
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            # 部分国产模型不支持 response_format：400 时降级重试一次
            degraded_json_mode = False
            if resp.status_code == 400 and self.json_mode:
                payload.pop("response_format", None)
                degraded_json_mode = True
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
            resp.raise_for_status()
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage") or {}
            stamp(
                trace, "extract", self.provider or "openai-compatible", started=t0, ok=True,
                model=self.model,
                base_url=self.base_url,
                provider=self.provider,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                json_mode_downgraded=degraded_json_mode,
            )
            return json.loads(content)

    async def chat(self, prompt: str, system: str = "", trace: Optional[list] = None,
                   want_json: bool = False) -> Optional[str]:
        """自由文本对话补全（Agent 规划器 / 回答生成用）。

        与 ``extract`` 的差别：返回原始字符串而非按 schema 解析的结果；
        ``mock`` 或未配置密钥时返回 ``None``，由调用方回退到确定性策略
        （保持「无 LLM 也能跑」的既有哲学）。异常一律吞掉返回 None。
        """
        import time

        from app.trace import stamp

        if self.provider == "mock" or not self.api_key:
            stamp(trace, "agent", self.provider or "mock", started=time.perf_counter(), ok=True,
                  model=self.model, fallback=True)
            return None

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict = {"model": self.model, "messages": messages}
        if want_json and self.json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                if resp.status_code == 400 and payload.get("response_format"):
                    payload.pop("response_format", None)
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                usage = (resp.json().get("usage") or {})
                stamp(trace, "agent", self.provider or "openai-compatible", started=t0, ok=True,
                      model=self.model, provider=self.provider,
                      total_tokens=usage.get("total_tokens"))
                return content.strip()
        except Exception as e:  # LLM 不可用不阻断 Agent：回退确定性策略
            stamp(trace, "agent", self.provider or "openai-compatible", ok=False, error=e,
                  model=self.model)
            return None
