"""作業級 LLM Trace（作業可觀測性）。

借鑒 Langfuse / Arize Phoenix 的最小可用形態：把一次作業中每一步
（抽取 / 富集 / 決策）的模型、耗時、token、成功與否記成一條**可導出的時間線**。
模型治理要求「這個結論是哪個模型、哪個版本、跑了多久產生的」——沒有 trace 就答不上來。
"""
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional


def new_trace() -> list:
    return []


def stamp(
    trace: Optional[list],
    kind: str,
    name: str,
    *,
    started: Optional[float] = None,
    ok: bool = True,
    error: Any = None,
    **extra: Any,
) -> Optional[dict]:
    """往 trace 時間線追加一步；trace 為 None 時靜默跳過（不影響主流程）。"""
    if trace is None:
        return None
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "name": name,
        "ok": bool(ok),
    }
    if started is not None:
        entry["duration_ms"] = int((time.perf_counter() - started) * 1000)
    if error:
        entry["error"] = str(error)[:300]
    entry.update(extra)
    trace.append(entry)
    return entry


@contextmanager
def span(trace: Optional[list], kind: str, name: str, **extra: Any):
    """同步代碼段的計時上下文（決策 / 解析器可用）。"""
    t0 = time.perf_counter()
    try:
        yield
        stamp(trace, kind, name, started=t0, ok=True, **extra)
    except Exception as e:  # 記錄失敗但不吞掉異常
        stamp(trace, kind, name, started=t0, ok=False, error=e, **extra)
        raise


def summary(trace: Optional[list]) -> dict:
    if not trace:
        return {"steps": 0}
    return {
        "steps": len(trace),
        "failed": [t.get("name") for t in trace if not t.get("ok", True)],
        "models": sorted({t.get("model") for t in trace if t.get("model")}),
        "total_ms": sum(int(t.get("duration_ms") or 0) for t in trace),
    }
