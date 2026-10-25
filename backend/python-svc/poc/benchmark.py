"""公開評測基準（Benchmark）：6 條業務線 × 繁中/英文/簡體的字段級抽取準確率。

與 Sixfold / Cytora 一樣把「怎麼評估」講清楚是建立信任的前提，因此這裡把評測集、
評測口徑與結果全部開源：
- 評測集：``data/samples/*.txt``（含繁中 / English / 简体三種語言形態）
- 口徑：**字段級**準確率（每條樣本逐字段比對，數值型按相等判定）
- 兩種模式：
  * 未配置 LLM_API_KEY → 規則/正則兜底基線（本機零成本可複現）
  * 配置 LLM_API_KEY   → 真實大模型準確率（可用同一評測集對比提升）

用法（在 backend/python-svc 下）：
    py poc/benchmark.py                # 打印表格
    py poc/benchmark.py --json         # 輸出機器可讀 JSON
    py poc/benchmark.py --write        # 同時寫入 docs/eval/benchmark.json
"""
import argparse
import asyncio
import json
import pathlib
import sys
from datetime import datetime, timezone

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from app.config import settings  # noqa: E402
from app.extraction import extract_document  # noqa: E402
from app.schemas import Vertical  # noqa: E402

SAMPLES = BASE / "data" / "samples"

CASES = [
    {
        "name": "insurance_hk · 繁體中文", "vertical": Vertical.insurance_hk,
        "file": "insurance_hk_sample_zh.txt",
        "expect": {"保单号": "HK12345", "投保人": "香港環宇保險有限公司", "受保人": "張三",
                   "险种": "終身壽險", "保额港币万": 800.0, "年缴保费港币万": 20.0,
                   "理赔金额港币万": 120.0, "KYC状态": "已完成"},
    },
    {
        "name": "insurance_hk · English", "vertical": Vertical.insurance_hk,
        "file": "insurance_hk_sample_en.txt",
        "expect": {"保单号": "HK9876543", "投保人": "Pacific Rich Ltd", "受保人": "Chan Tai Man",
                   "保额港币万": 800.0, "年缴保费港币万": 20.0, "理赔金额港币万": 120.0},
    },
    {
        "name": "insurance_hk · 简体中文", "vertical": Vertical.insurance_hk,
        "file": "insurance_hk_sample_cn.txt",
        "expect": {"保单号": "HK12345", "投保人": "香港环宇保险有限公司", "受保人": "张三",
                   "险种": "终身寿险", "保额港币万": 800.0, "年缴保费港币万": 20.0,
                   "理赔金额港币万": 120.0, "KYC状态": "完成"},
    },
    {
        "name": "family_office · 繁體中文", "vertical": Vertical.family_office,
        "file": "family_office_sample_zh.txt",
        "expect": {"客户姓名或实体名称": "陳大文家族辦公室有限公司", "身份类型": "公司（家族辦公室）",
                   "资产规模港币万": 50000.0, "资金来源": "家族持股出售所得",
                   "受益所有人": "陳大文", "风险等级": "中", "KYC状态": "待補"},
    },
    {
        "name": "banking_mortgage · 繁體中文", "vertical": Vertical.banking_mortgage,
        "file": "banking_mortgage_sample_zh.txt",
        "expect": {"申请人": "李小明", "物业估值港币万": 1000.0, "贷款金额港币万": 700.0,
                   "贷款成数LTV": 0.7, "月收入港币": 80000.0, "月负债供款港币": 50000.0,
                   "供款入息比率DSR": 0.62, "物业类型": "住宅", "首期资金来源": "储蓄",
                   "KYC状态": "完成"},
    },
    {
        "name": "securities_suitability · 繁體中文", "vertical": Vertical.securities_suitability,
        "file": "securities_suitability_sample_zh.txt",
        "expect": {"客户姓名或实体名称": "王五", "风险承受度": "低", "产品风险等级": "高",
                   "投资经验年": 1.0, "财务状况港币": 2000000.0, "投资知识水平": "低",
                   "产品类型": "衍生品", "KYC状态": "完成"},
    },
    {
        "name": "mpf · 繁體中文", "vertical": Vertical.mpf,
        "file": "mpf_sample_zh.txt",
        "expect": {"成员姓名或实体名称": "陳六", "计划类型": "強積金", "雇主名称": "某某有限公司",
                   "雇员状态": "在職", "雇主登记状态": "未登記", "供款状态": "正常",
                   "自愿供款": "無", "KYC状态": "完成"},
    },
    {
        "name": "fund_ofc_lpf · 繁體中文", "vertical": Vertical.fund_ofc_lpf,
        "file": "fund_ofc_lpf_sample_zh.txt",
        "expect": {"基金名称或实体名称": "環宇機會基金", "结构类型": "OFC",
                   "是否获证监会认可": "否", "管理公司": "環宇資產管理",
                   "投资者类型": "零售", "受益所有人": "張三",
                   "募资规模港币万": 5000.0, "KYC状态": "完成"},
    },
]


def _match(got, want) -> bool:
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return abs(float(got) - float(want)) < 1e-6
    return got == want


async def run() -> dict:
    # 未配置密钥时为规则/正则兜底基线；配置后为真实模型准确率
    mode = "rule-fallback" if (settings.llm_provider == "mock" or not settings.llm_api_key) else "llm"
    rows, total_ok, total_all = [], 0, 0
    for case in CASES:
        text = (SAMPLES / case["file"]).read_text(encoding="utf-8")
        got = (await extract_document(text, case["vertical"]))["extracted"]
        expect = case["expect"]
        misses = []
        for k, v in expect.items():
            if not _match(got.get(k), v):
                misses.append({"field": k, "expect": v, "got": got.get(k)})
        ok = len(expect) - len(misses)
        total_ok += ok
        total_all += len(expect)
        rows.append({
            "case": case["name"],
            "vertical": case["vertical"].value,
            "fields": len(expect),
            "correct": ok,
            "accuracy": round(ok / len(expect), 4),
            "misses": misses,
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "llm_provider": settings.llm_provider,
        "metric": "field-level exact match",
        "total_fields": total_all,
        "total_correct": total_ok,
        "accuracy": round(total_ok / total_all, 4) if total_all else 0,
        "cases": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--write", action="store_true", help="写入 docs/eval/benchmark.json")
    ap.add_argument(
        "--fail-under", type=float, default=None, metavar="RATIO",
        help="回归门禁：总体字段级准确率低于该阈值（0~1，如 0.95）时以非 0 退出码失败，供 CI 拦截质量回退",
    )
    args = ap.parse_args()

    report = asyncio.run(run())

    if args.write:
        out = BASE.parents[1] / "docs" / "eval" / "benchmark.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("=" * 78)
    print(f"Ceron 抽取評測基準 · 模式={report['mode']} · 指標={report['metric']}")
    print("=" * 78)
    for r in report["cases"]:
        print(f"  {r['case']:<34} {r['accuracy']:>6.0%}  ({r['correct']}/{r['fields']})")
        for m in r["misses"]:
            print(f"      MISS {m['field']}: 期望={m['expect']!r} 实际={m['got']!r}")
    print("-" * 78)
    print(f"  总体字段级准确率: {report['accuracy']:.0%} ({report['total_correct']}/{report['total_fields']})")
    print("  说明：rule-fallback 为未配置密钥时的兜底基线；配置 LLM_API_KEY 后重跑即得真实模型准确率。")

    if args.fail_under is not None:
        acc = report["accuracy"]
        gate_ok = acc >= args.fail_under
        print("-" * 78)
        print(f"  回归门禁 (--fail-under {args.fail_under:.0%}): {'PASS' if gate_ok else 'FAIL'} "
              f"(实测 {acc:.0%})")
        if not gate_ok:
            print("  质量回退：抽取准确率低于门禁阈值。请检查正则兜底规则或 schema 配置的改动。")
            raise SystemExit(1)


if __name__ == "__main__":
    main()
