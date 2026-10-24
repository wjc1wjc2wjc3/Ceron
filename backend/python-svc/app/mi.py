"""监管 MI 报表：面向 SFC / HKMA / 保监局 的统计与报送聚合。

基于内存中的决策历史、监控告警与 SAR，输出可嵌入看板的汇总指标。
"""
from app import store


def build_mi_report() -> dict:
    runs = store.list_runs()
    by_vertical: dict[str, int] = {}
    by_action: dict[str, int] = {}
    high_risk = 0
    for r in runs:
        by_vertical[r["vertical"]] = by_vertical.get(r["vertical"], 0) + 1
        by_action[r["action"]] = by_action.get(r["action"], 0) + 1
        if r["risk_score"] >= 60:
            high_risk += 1

    sars = store.list_sars()
    return {
        "generated_at": store.now_iso(),
        "total_decisions": len(runs),
        "by_vertical": by_vertical,
        "by_action": by_action,
        "high_risk_count": high_risk,
        "open_alerts": len(store.list_alerts()),
        "sars_total": len(sars),
        "sars_by_status": store._count(sars, "status"),
    }
