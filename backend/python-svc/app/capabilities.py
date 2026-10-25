"""能力覆盖度（Capabilities）：把「我们到底覆盖了多少」变成**可查询、可对外引用**的数字。

竞品都在用可量化覆盖度建立信任（Dilly「40 条规则」、Masttro「750+ 数据源」、
Neutrinos「预建保险方案」）。这里把业务线、数据源、闸口规则、模型预设、解析器
统一统计后暴露为接口，供 README / 落地页 / 竞品对比页直接引用，避免各处手写数字不一致。
"""
from app import rules
from app.enrichment import get_configured_providers
from app.llm_catalog import PRESETS
from app.parsers import list_parsers
from app.schemas import Vertical

# 已实现的数据源 Provider（是否被启用取决于 .env 中 *_API_URL 是否配置）
PROVIDER_CATALOG = [
    {"id": "icris", "name": "香港公司註冊處 ICRIS 查冊"},
    {"id": "land_search", "name": "土地註冊處 Land Search"},
    {"id": "credit_bureau", "name": "信貸資料庫"},
    {"id": "sanctions", "name": "制裁名單（外部服務）"},
    {"id": "ofac", "name": "OFAC SDN"},
    {"id": "hmt", "name": "HMT 綜合名單"},
    {"id": "crs", "name": "CRS / FATCA 稅務居民"},
]


def snapshot(locale: str = "zh-HK") -> dict:
    configured = [getattr(p, "name", type(p).__name__) for p in get_configured_providers()]
    by_gate: dict[str, int] = {}
    for r in rules.RULES:
        by_gate[r.gate] = by_gate.get(r.gate, 0) + 1

    return {
        "verticals": {
            "count": len(list(Vertical)),
            "items": [v.value for v in Vertical],
        },
        "data_sources": {
            "implemented": len(PROVIDER_CATALOG),
            "configured": len(configured),
            "items": [
                {**p, "enabled": p["id"] in configured} for p in PROVIDER_CATALOG
            ],
        },
        "compliance_gates": {
            "rules": len(rules.RULES),
            "gates": sorted(by_gate.keys()),
            "by_gate": by_gate,
            "version": rules.RULE_PACK_VERSION,
        },
        "models": {
            "presets": len(PRESETS),
            "items": sorted(p["id"] for p in PRESETS),
            "custom": "openai-compatible",
        },
        "parsers": list_parsers(locale),
        "review_checkpoints": 10,   # 见 app/review.py
        "languages": ["zh-HK", "en", "zh-CN"],
    }
