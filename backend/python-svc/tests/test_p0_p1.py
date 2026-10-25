"""P0/P1 能力：规则包版本化、HITL 分级、UBO 图穿透、作业级 trace、
能力覆盖度、审计包导出、可插拔解析器与 MCP 工具层。"""
from fastapi.testclient import TestClient

from app import rules
from app.capabilities import snapshot
from app.decision import assess, assess_with_review
from app.main import app
from app.parsers import list_parsers
from app.review import build_review
from app.schemas import Vertical
from app.ubo import resolve as resolve_ubo

client = TestClient(app)


# ---------- 规则包（P1-3）----------
def test_rule_pack_export_has_gates_and_version():
    pack = rules.export()
    assert pack["version"] == rules.RULE_PACK_VERSION
    assert pack["count"] == len(rules.RULES) > 0
    assert {"SFC", "HKMA", "MPFA", "AML"} <= set(pack["gates"])


def test_rule_execution_record_is_structured():
    ex = {"贷款成数LTV": 0.7, "供款入息比率DSR": 0.3, "首期资金来源": "储蓄", "KYC状态": "完成"}
    run = rules.evaluate("banking_mortgage", ex, {}, locale="zh-HK", completeness=1.0)
    assert run["score"] == 30
    assert any(h["id"] == "HKMA.mortgage.ltv_above_cap" for h in run["hits"])
    assert run["hits"][0]["gate"] == "HKMA"


def test_decision_carries_rule_pack_and_band():
    ex = {"雇主登记状态": "未登记", "雇员状态": "在职", "供款状态": "正常", "KYC状态": "完成"}
    d = assess(Vertical.mpf, ex, {}, "zh-HK")
    assert d["rule_pack"]["version"] == rules.RULE_PACK_VERSION
    assert d["risk_level"] in ("low", "medium", "high", "critical")
    assert d["gates"] == ["MPFA"]
    assert d["evidence"][0]["rule"] == "MPFA.employer_not_registered"


def test_risk_band_thresholds():
    assert rules.band_of(0)[1] == "approve"
    assert rules.band_of(30)[1] == "manual_review"
    assert rules.band_of(70)[1] == "reject"
    assert rules.band_of(90)[0] == "critical"


# ---------- HITL 分级（P1-4）----------
def test_review_level_source_on_degraded_enrichment():
    ex = {"KYC状态": "完成", "资金来源": "薪金"}
    enr = {"flags": ["信貸局查詢失敗：需人工複核。"], "provider": "credit_bureau"}
    d = assess(Vertical.family_office, ex, enr, "zh-HK")
    rv = build_review("family_office", ex, enr, d, [], "zh-HK")
    assert rv["level"] == "source"
    assert any(cp["id"] == "CP-05" for cp in rv["checkpoints"])


def test_review_level_gate_on_sanctions():
    ex = {"KYC状态": "完成", "资金来源": "薪金", "客户姓名或实体名称": "X"}
    enr = {"sanctions_hit": True}
    d = assess_with_review(Vertical.family_office, ex, enr, "zh-HK")
    # 制裁命中既是 gate 级，又把风险带位推到 high → 最终级别取最重的 risk
    assert d["review"]["level"] == "risk"
    assert any(cp["id"] == "CP-06" for cp in d["review"]["checkpoints"])
    assert d["action"] == "reject"


def test_review_none_for_clean_case():
    ex = {"贷款成数LTV": 0.5, "供款入息比率DSR": 0.4, "首期资金来源": "储蓄", "KYC状态": "完成"}
    d = assess_with_review(Vertical.banking_mortgage, ex, {}, "zh-HK")
    assert d["review"]["level"] == "none"
    assert d["review"]["required"] is False


# ---------- UBO 图穿透（P1-6）----------
def test_ubo_two_layer_multiplication():
    edges = [{"from": "HoldCo", "to": "MidCo", "pct": 60}, {"from": "MidCo", "to": "陳大文", "pct": 50}]
    out = resolve_ubo({"客户姓名或实体名称": "HoldCo"}, edges)
    owner = next(o for o in out["beneficial_owners"] if o["name"] == "陳大文")
    assert abs(owner["pct"] - 0.30) < 1e-6      # 60% × 50% = 30%
    assert owner["above_threshold"] is True
    assert owner["path"] == ["HoldCo", "MidCo", "陳大文"]
    assert out["mode"] == "graph"


def test_ubo_detects_cycle():
    edges = [{"from": "A", "to": "B", "pct": 50}, {"from": "B", "to": "A", "pct": 50}]
    out = resolve_ubo({"客户姓名或实体名称": "A"}, edges)
    assert out["cycles"]


def test_ubo_fallback_from_text():
    out = resolve_ubo({"受益所有人": "陳大文 60%、陳小文 40%"})
    assert out["mode"] == "fallback"
    assert any(o["name"] == "陳大文" for o in out["beneficial_owners"])


# ---------- 能力覆盖度（P0-1）----------
def test_capabilities_snapshot_matches_implementation():
    cap = snapshot("zh-HK")
    assert cap["verticals"]["count"] == len(list(Vertical))
    assert cap["compliance_gates"]["rules"] == len(rules.RULES)
    assert cap["compliance_gates"]["version"] == rules.RULE_PACK_VERSION
    assert cap["data_sources"]["implemented"] >= 7
    assert cap["models"]["presets"] >= 5
    assert cap["parsers"]["parsers"][-1]["available"] is True   # 内置解析器永远可用


# ---------- 解析器（P1-1）----------
def test_parsers_registry_exposes_internal_fallback():
    reg = list_parsers("en")
    ids = [p["id"] for p in reg["parsers"]]
    assert "internal" in ids and "paddleocr" in ids and "docling" in ids
    assert any(p["available"] for p in reg["parsers"])


# ---------- 端到端：pipeline → trace → 审计包（P0-4 / P1-2）----------
def test_pipeline_returns_run_id_trace_and_audit_pack():
    text = (
        "客户姓名：陳大文家族辦公室有限公司\n身份類型：公司（家族辦公室）\n"
        "資產規模：50000萬港元\n資金來源：家族持股出售所得\n"
        "受益所有人：陳大文\n風險等級：中\nKYC狀態：完成"
    )
    r = client.post("/v1/pipeline", json={"vertical": "family_office", "text": text, "locale": "zh-HK"})
    assert r.status_code == 200
    body = r.json()
    run_id = body["run_id"]
    assert run_id.startswith("PY-")
    assert body["trace"] and body["trace_summary"]["steps"] >= 1
    assert body["decision"]["rule_pack"]["version"] == rules.RULE_PACK_VERSION
    assert "beneficial_owners" in body["ubo"]

    a = client.get(f"/v1/runs/{run_id}/audit")
    assert a.status_code == 200
    pack = a.json()
    assert pack["schema_version"] == "ceron-audit-1.0"
    assert pack["rule_pack"]["version"] == rules.RULE_PACK_VERSION
    assert isinstance(pack["evidence"], list)
    assert pack["extracted"] and pack["trace"]

    missing = client.get("/v1/runs/PY-not-exist/audit")
    assert missing.status_code == 404


def test_ownership_edges_flow_through_pipeline():
    text = "客户姓名：HoldCo\n資產規模：1000萬港元\n資金來源：出售股權\nKYC狀態：完成"
    edges = [{"from": "HoldCo", "to": "陳大文", "pct": 80}]
    r = client.post("/v1/pipeline", json={
        "vertical": "family_office", "text": text, "ownership_edges": edges,
    })
    assert r.status_code == 200
    ubo = r.json()["ubo"]
    assert ubo["mode"] == "graph"
    assert ubo["beneficial_owners"][0]["pct"] == 0.8


# ---------- MCP（P1-5）----------
def test_mcp_tools_list_and_call():
    tools = client.get("/v1/mcp/tools").json()["tools"]
    names = {t["name"] for t in tools}
    assert {"ceron.extract", "ceron.enrich", "ceron.decide", "ceron.ubo", "ceron.rules"} == names

    rpc = client.post("/v1/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "ceron.rules", "arguments": {}},
    }).json()
    assert "result" in rpc
    assert rpc["result"]["structuredContent"]["version"] == rules.RULE_PACK_VERSION

    bad = client.post("/v1/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "nope"}).json()
    assert bad["error"]["code"] == -32601


def test_mcp_ubo_call():
    rpc = client.post("/v1/mcp", json={
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "ceron.ubo", "arguments": {
            "extracted": {"客户姓名或实体名称": "A"},
            "ownership_edges": [{"from": "A", "to": "B", "pct": 30}],
        }},
    }).json()
    assert rpc["result"]["structuredContent"]["beneficial_owners"][0]["name"] == "B"


# ---------- 规则包导出接口 ----------
def test_rules_endpoint_filters_by_vertical():
    all_pack = client.get("/v1/rules").json()
    mpf = client.get("/v1/rules?vertical=mpf").json()
    assert mpf["count"] < all_pack["count"]
    assert all(r["vertical"] in ("*", "mpf") for r in mpf["rules"])
    assert client.get("/v1/rules/version").json()["version"] == rules.RULE_PACK_VERSION
