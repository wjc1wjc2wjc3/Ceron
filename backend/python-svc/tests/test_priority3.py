"""优先级 3：持续监控 / SAR 申报 / 监管 MI 的单元测试。"""
from app import store, monitoring, sar, mi


def test_store_record_and_mi():
    store.pipeline_runs.clear()
    store.entities.clear()
    store.record_run("insurance_hk", "approve", 10, name="测试实体A")
    assert len(store.list_runs()) == 1
    assert any(e["name"] == "测试实体A" for e in store.list_entities())
    rep = mi.build_mi_report()
    assert rep["total_decisions"] == 1
    assert rep["by_vertical"].get("insurance_hk") == 1


def test_monitoring_scan_alert():
    store.entities.clear()
    store.alerts.clear()
    store.record_run("family_office", "approve", 0, name="OFAC 坏人")
    hits = monitoring.run_scan()  # 复用 enrich：OFAC 关键字命中
    assert "OFAC 坏人" in hits
    assert len(store.list_alerts()) >= 1


def test_sar_create_and_status():
    s = sar.create_sar("张三", "banking_mortgage", "制裁命中", {})
    assert s["status"] == "draft"
    s2 = sar.set_status(s["id"], "submitted")
    assert s2["status"] == "submitted"


def test_mi_aggregates_actions():
    store.pipeline_runs.clear()
    store.record_run("mpf", "reject", 70, name="X")
    store.record_run("mpf", "manual_review", 30, name="Y")
    rep = mi.build_mi_report()
    assert rep["high_risk_count"] == 1
    assert rep["by_action"].get("reject") == 1
    assert rep["by_action"].get("manual_review") == 1
