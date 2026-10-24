"""端到端富集验证：正则抽取 → 富集（ICRIS/制裁名单，配置后走真实服务）→ 决策。

- 未配置 ICRIS_API_URL / SANCTIONS_API_URL：走 mock 基线（离线可跑）。
- 配置后：对应 Provider 实际调用并合并结果；失败自动降级打「需人工複核」标记。
运行：py poc/e2e_enrichment.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402
from app.decision import assess  # noqa: E402
from app.enrichment import enrich  # noqa: E402
from app.regex_extract import rule_extract  # noqa: E402
from app.schemas import Vertical  # noqa: E402

SAMPLES = {
    Vertical.insurance_hk: (
        "投保人：香港環宇保險有限公司\n保單號：HK12345\n受保人：張三\n險種：終身壽險\n"
        "保額：800萬\n年繳保費：20萬\n理賠類型：身故\n理賠金額：120萬"
    ),
    Vertical.family_office: (
        "客戶姓名：陳大文家族辦公室有限公司\n身份類型：公司\n"
        "資產規模：50,000萬港元\n資金來源：家族持股出售所得\n受益所有人：陳大文\nKYC狀態：待補"
    ),
}


def main() -> None:
    active = []
    if settings.icris_api_url:
        active.append(f"icris({settings.icris_api_url})")
    if settings.sanctions_api_url:
        active.append(f"sanctions({settings.sanctions_api_url})")
    print("富集数据源：", " + ".join(active) if active else "mock（未配置 ICRIS/SANCTIONS）")

    for vertical, text in SAMPLES.items():
        extracted = rule_extract(text)
        enrichment = enrich(vertical.value, extracted)
        decision = assess(vertical, extracted, enrichment)
        print(f"\n=== {vertical.value} ===")
        print("provider:", enrichment["provider"])
        print(
            "icris_verified:", enrichment["icris_verified"],
            "| sanctions_hit:", enrichment["sanctions_hit"],
            "| risk:", enrichment["risk_from_enrich"],
        )
        print("flags:", enrichment["flags"])
        print("decision:", decision["action"], "| risk_score:", decision["risk_score"])
        for r in decision["reasons"]:
            print("  -", r)


if __name__ == "__main__":
    main()
