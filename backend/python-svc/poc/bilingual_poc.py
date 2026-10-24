"""双语抽取准确率 PoC：繁中/英文样本的字段级抽取准确率评估。

离线（mock 正则）与真实 LLM 均可运行；接密钥后重跑可对比提升。

用法（在 backend/python-svc 下）:
    py poc/bilingual_poc.py
"""
import asyncio
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from app.extraction import extract_document  # noqa: E402
from app.schemas import Vertical  # noqa: E402

CASES = [
    {
        "name": "insurance_hk 繁體中文",
        "vertical": Vertical.insurance_hk,
        "file": "insurance_hk_sample_zh.txt",
        "expect": {
            "保单号": "HK12345",
            "投保人": "香港環宇保險有限公司",
            "受保人": "張三",
            "险种": "終身壽險",
            "保额港币万": 800.0,
            "年缴保费港币万": 20.0,
            "理赔金额港币万": 120.0,
            "KYC状态": "已完成",
        },
    },
    {
        "name": "insurance_hk English",
        "vertical": Vertical.insurance_hk,
        "file": "insurance_hk_sample_en.txt",
        "expect": {
            "保单号": "HK9876543",
            "投保人": "Pacific Rich Ltd",
            "受保人": "Chan Tai Man",
            "保额港币万": 800.0,
            "年缴保费港币万": 20.0,
            "理赔金额港币万": 120.0,
        },
    },
    {
        "name": "family_office 繁體中文",
        "vertical": Vertical.family_office,
        "file": "family_office_sample_zh.txt",
        "expect": {
            "客户姓名或实体名称": "陳大文家族辦公室有限公司",
            "身份类型": "公司（家族辦公室）",
            "资产规模港币万": 50000.0,
            "资金来源": "家族持股出售所得",
            "受益所有人": "陳大文",
            "风险等级": "中",
            "KYC状态": "待補",
        },
    },
]


def _match(got, want) -> bool:
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return abs(got - want) < 1e-6
    return got == want


async def main() -> None:
    total_ok = total_all = 0
    print("=" * 72)
    for case in CASES:
        text = (BASE / "data" / "samples" / case["file"]).read_text(encoding="utf-8")
        res = await extract_document(text, case["vertical"])
        got = res["extracted"]
        expect = case["expect"]
        oks = []
        for k, v in expect.items():
            ok = _match(got.get(k), v)
            oks.append(ok)
            mark = "PASS" if ok else "MISS"
            print(f"  [{mark}] {k}: 期望={v!r} 实际={got.get(k)!r}")
        acc = sum(oks) / len(oks)
        total_ok += sum(oks)
        total_all += len(oks)
        print(f"{case['name']}: 准确率 {acc:.0%} ({sum(oks)}/{len(oks)})")
        print("-" * 72)
    print(f"总体字段级准确率: {total_ok / total_all:.0%} ({total_ok}/{total_all})")
    print("说明：mock(正则)模式下为兜底基线；配置 LLM_API_KEY 后重跑可得真实模型准确率。")


if __name__ == "__main__":
    asyncio.run(main())
