"""可疑交易申报（SAR / JFIU）：生成与留痕。

高风险决策（制裁命中、reject、manual_review 高風險）应触发 SAR 申报评估。
本模块提供创建（草稿）、查询与状态流转（draft → submitted → closed）的轻量实现。
"""
from typing import Any, Optional

from app import store


def create_sar(name: str, vertical: str, reason: str, decision_summary: Optional[dict] = None) -> dict:
    """创建一份 SAR 草稿（status=draft）。"""
    return store.add_sar({
        "name": name,
        "vertical": vertical,
        "reason": reason,
        "decision_summary": decision_summary or {},
    })


def list_sars() -> list:
    return store.list_sars()


def set_status(sar_id: str, status: str) -> Optional[dict]:
    """流转 SAR 状态：draft → submitted（已提交 JFIU）/ closed。"""
    return store.update_sar(sar_id, status)
