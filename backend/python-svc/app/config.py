"""Ceron 配置：从环境变量读取，集中管理 LLM、OCR、富集数据源、数据驻留与脱敏开关。"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # 自动加载同目录 .env（密钥不进命令行、不入版本库）


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
    # mock | icris | sanctions（遗留单源选择）
    enrichment_provider: str = os.getenv("ENRICHMENT_PROVIDER", "mock")
    icris_api_url: str = os.getenv("ICRIS_API_URL", "")
    icris_api_key: str = os.getenv("ICRIS_API_KEY", "")
    # ICRIS 会话态鉴权（e-Services / 持牌数据服务商）：登录换 token 后以 Bearer 查询
    icris_auth_url: str = os.getenv("ICRIS_AUTH_URL", "")
    icris_account: str = os.getenv("ICRIS_ACCOUNT", "")
    sanctions_api_url: str = os.getenv("SANCTIONS_API_URL", "")
    sanctions_api_key: str = os.getenv("SANCTIONS_API_KEY", "")
    # 优先级 1 新增数据源（配置对应 API_URL 即启用，失败自动降级人工复核）
    land_search_api_url: str = os.getenv("LAND_SEARCH_API_URL", "")
    land_search_api_key: str = os.getenv("LAND_SEARCH_API_KEY", "")
    credit_bureau_api_url: str = os.getenv("CREDIT_BUREAU_API_URL", "")
    credit_bureau_api_key: str = os.getenv("CREDIT_BUREAU_API_KEY", "")
    # 信贷局会员鉴权（TransUnion HK 等以会员编号 + API Key 调用）
    credit_bureau_member_id: str = os.getenv("CREDIT_BUREAU_MEMBER_ID", "")
    ofac_api_url: str = os.getenv("OFAC_API_URL", "")
    ofac_api_key: str = os.getenv("OFAC_API_KEY", "")
    hmt_api_url: str = os.getenv("HMT_API_URL", "")
    hmt_api_key: str = os.getenv("HMT_API_KEY", "")
    crs_api_url: str = os.getenv("CRS_API_URL", "")
    crs_api_key: str = os.getenv("CRS_API_KEY", "")
    # ===== 优先级 3：持续监控（Ongoing Monitoring）=====
    # 是否启用后台周期性重查调度（默认关闭；生产建议开启以符合持续尽职要求）
    monitoring_enabled: bool = str(os.getenv("MONITORING_ENABLED", "false")).lower() == "true"
    monitoring_interval: int = int(os.getenv("MONITORING_INTERVAL_SECONDS", "300"))
    # ===== 持久化（与 go-svc jobs 表对齐）=====
    # 配置 DATABASE_URL 即切到 Postgres（JSONB 持久化）；未配置/连接失败回退内存。
    # 建议与 go-svc 共用同一实例，使 Go 看板与 Python 决策历史落在同一 jobs 表。
    database_url: str = os.getenv("DATABASE_URL", "")
    # ===== 认证（Auth：邮箱密码 + X / Facebook 第三方登录）=====
    # 会话令牌签名密钥（生产务必更换；须与前端 AUTH_SECRET 一致，便于 Next 校验会话）
    auth_secret: str = os.getenv("AUTH_SECRET", "ceron-dev-secret-change-me")
    auth_token_ttl: int = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(7 * 24 * 3600)))
    # 前后端地址：OAuth 回调需要外网可达的绝对 URL
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    # X (Twitter) OAuth 2.0 App；配置 X_CLIENT_ID 即启用「使用 X 登录」
    x_client_id: str = os.getenv("X_CLIENT_ID", "")
    x_client_secret: str = os.getenv("X_CLIENT_SECRET", "")
    x_redirect_uri: str = os.getenv("X_REDIRECT_URI", f"{public_base_url}/v1/auth/x/callback")
    # Facebook 登录
    facebook_client_id: str = os.getenv("FACEBOOK_CLIENT_ID", "")
    facebook_client_secret: str = os.getenv("FACEBOOK_CLIENT_SECRET", "")
    facebook_redirect_uri: str = os.getenv(
        "FACEBOOK_REDIRECT_URI", f"{public_base_url}/v1/auth/facebook/callback")


settings = Settings()
