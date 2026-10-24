"""合规运营状态存储（内存版，零外部依赖，默认构建即可跑）。

用于持续监控、SAR 申报与监管 MI 报表的轻量状态机：
- pipeline_runs：决策历史（供 MI 聚合）
- entities：已登记实体（供持续监控重查）
- alerts：监控告警
- sars：可疑交易申报（JFIU）

生产建议替换为 Postgres（与 go-svc 作业表一致的持久化），此处为 POC 提供可运行闭环。
"""
import threading
from datetime import datetime, timezone
from typing import Any, Optional


_lock = threading.Lock()
pipeline_runs: list[dict] = []
entities: list[dict] = []
alerts: list[dict] = []
sars: list[dict] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_run(vertical: str, action: str, risk_score: int, name: Optional[str] = None) -> None:
    """记录一次决策结果，并登记实体供持续监控。"""
    with _lock:
        pipeline_runs.append({
            "ts": now_iso(),
            "vertical": vertical,
            "action": action,
            "risk_score": risk_score,
            "name": name,
        })
        if name:
            if not any(e["name"] == name for e in entities):
                entities.append({"name": name, "vertical": vertical, "ts": now_iso()})


def list_runs() -> list[dict]:
    with _lock:
        return list(pipeline_runs)


def list_entities() -> list[dict]:
    with _lock:
        return list(entities)


def add_alert(name: str, reason: str, lists: Optional[list] = None) -> dict:
    with _lock:
        a = {
            "id": len(alerts) + 1,
            "ts": now_iso(),
            "name": name,
            "reason": reason,
            "lists": lists or [],
            "status": "open",
        }
        alerts.append(a)
        return a


def list_alerts() -> list[dict]:
    with _lock:
        return list(alerts)


def add_sar(payload: dict) -> dict:
    with _lock:
        s = {
            "id": f"SAR-{len(sars) + 1:04d}",
            "ts": now_iso(),
            "status": "draft",
            **payload,
        }
        sars.append(s)
        return s


def list_sars() -> list[dict]:
    with _lock:
        return list(sars)


def update_sar(sar_id: str, status: str) -> Optional[dict]:
    with _lock:
        for s in sars:
            if s["id"] == sar_id:
                s["status"] = status
                return s
        return None


def _count(items: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for it in items:
        out[it.get(key, "unknown")] = out.get(it.get(key, "unknown"), 0) + 1
    return out
