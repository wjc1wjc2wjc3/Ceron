"""Ceron 配置：从环境变量读取，集中管理 LLM、OCR、富集数据源、数据驻留与脱敏开关。"""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    app_name: str = "Ceron"
    # ===== LLM =====
    # mock(无密钥) | deepseek | qwen | glm | openai | claude
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    # ===== 数据合规 =====
    # 数据驻留区域：hk(中国香港) / cn(中国内地)
    data_region: str = os.getenv("DATA_REGION", "hk")
    enable_pii_masking: bool = str(os.getenv("ENABLE_PII_MASKING", "true")).lower() == "true"
    # ===== OCR =====
    # mock | azure | tesseract
    ocr_provider: str = os.getenv("OCR_PROVIDER", "mock")
    azure_form_endpoint: str = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT", "")
    azure_form_key: str = os.getenv("AZURE_FORM_RECOGNIZER_KEY", "")
    # ===== Enrichment（富集数据源）=====
    # mock | icris | sanctions
    enrichment_provider: str = os.getenv("ENRICHMENT_PROVIDER", "mock")
    icris_api_url: str = os.getenv("ICRIS_API_URL", "")
    icris_api_key: str = os.getenv("ICRIS_API_KEY", "")
    sanctions_api_url: str = os.getenv("SANCTIONS_API_URL", "")
    sanctions_api_key: str = os.getenv("SANCTIONS_API_KEY", "")


settings = Settings()
