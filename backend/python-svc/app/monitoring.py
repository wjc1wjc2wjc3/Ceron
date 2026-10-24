"""持续尽职（Ongoing Monitoring）：触发式 re-KYC 与周期性重查。

- 触发式：重大事件（制裁名单更新、实体状态变更）触发对已登记实体的重查。
- 周期性：后台调度线程按间隔对 entities 重新跑富集（制裁/OFAC/HMT 等），
  命中即生成告警并留痕，保证「一次性 onboarding」扩展为「持续监控」。
"""
import threading
import time

from app import store
from app.enrichment import enrich


def screen_entity(name: str) -> dict:
    """对已登记实体重新跑富集（复用全部已配置 Provider），返回命中结果。"""
    return enrich("family_office", {"客户姓名或实体名称": name}, locale="zh-HK")


def run_scan() -> list:
    """对所有已登记实体重查制裁/PEP，命中写入告警。返回命中实体名列表。"""
    hits: list[str] = []
    for e in store.list_entities():
        res = screen_entity(e["name"])
        if res.get("sanctions_hit"):
            store.add_alert(e["name"], "制裁/PEP 名单重查命中", res.get("sanctions_lists", []))
            hits.append(e["name"])
    return hits


_scheduler = None


def start_scheduler(interval: int = 300) -> None:
    """启动周期性重查调度线程（守护线程，进程退出自动结束）。"""
    global _scheduler
    if _scheduler is not None:
        return

    def _loop() -> None:
        while True:
            time.sleep(interval)
            try:
                run_scan()
            except Exception:
                # 调度循环不因单次失败中断
                pass

    _scheduler = threading.Thread(target=_loop, daemon=True)
    _scheduler.start()
