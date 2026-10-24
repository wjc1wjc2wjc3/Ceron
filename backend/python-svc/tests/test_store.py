"""store 后端测试：默认内存模式（无 DATABASE_URL）的决策历史 / 告警 / SAR 闭环。

若运行环境已配置 DATABASE_URL，则跳过（Postgres 路径需真实数据库，另行集成验证）。
"""
import os

import pytest

import app.store as store

pytestmark = pytest.mark.skipif(
    bool(os.getenv("DATABASE_URL")),
    reason="仅验证内存后端；配置 DATABASE_URL 时使用 Postgres 后端",
)


def setup_function(fn):
    for lst in (store.pipeline_runs, store.entities, store.alerts, store.sars):
        lst.clear()


def test_memory_backend_selected_when_no_db():
    assert store._pg is None


def test_record_run_and_list():
    store.record_run("insurance_hk", "approve", 10, name="实体X")
    assert len(store.list_runs()) == 1
    r = store.list_runs()[0]
    assert r["action"] == "approve" and r["risk_score"] == 10
    assert any(e["name"] == "实体X" for e in store.list_entities())


def test_alert_and_sar_roundtrip():
    a = store.add_alert("坏人", "制裁命中", ["OFAC"])
    assert a["status"] == "open" and a["id"] >= 1
    assert len(store.list_alerts()) == 1

    s = store.add_sar({"name": "坏人", "reason": "可疑", "vertical": "banking_mortgage"})
    assert s["status"] == "draft" and s["id"].startswith("SAR-")
    assert len(store.list_sars()) == 1

    updated = store.update_sar(s["id"], "submitted")
    assert updated is not None and updated["status"] == "submitted"
    assert store.update_sar("SAR-9999", "submitted") is None
