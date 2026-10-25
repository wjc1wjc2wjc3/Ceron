"""块1：法规速检知识库（RAG 引用）+ 合规 Agent 闭环（规划→工具调用→反思）。"""
import pytest
from fastapi.testclient import TestClient

from app import agent, kb
from app.main import app

client = TestClient(app)


@pytest.fixture
def anyio_backend():
    """未安装 trio：限定 anyio 只跑 asyncio 后端。"""
    return "asyncio"


# ---------------- KB（可引用的监管依据）----------------
def test_kb_search_returns_citable_source():
    hits = kb.search("適合性 客戶建議 投資目標", vertical="securities_suitability", top_k=3)
    assert hits, "检索应有命中"
    top = hits[0]
    assert top["id"] == "SFC-SUIT-01"
    assert top["source"] and top["title"] and top["text"]
    assert "score" in top


def test_kb_search_filters_by_vertical():
    hits = kb.search("提取 累算權益", vertical="mpf", top_k=3)
    assert hits
    ids = [h["id"] for h in hits]
    assert "MPFA-MPF-02" in ids
    assert all("mpf" in h["verticals"] or "*" in h["verticals"] for h in hits)


def test_kb_search_empty_query_safe():
    assert kb.search("", top_k=3) == []
    assert kb.search("完全无关的随机字符串zzzz", top_k=3) == []


def test_t2s_table_pairs_are_valid():
    """每个条目必须是「繁+简」两字一组，防止表格被改坏。"""
    pairs = kb._T2S_PAIRS.split()
    assert pairs and all(len(p) == 2 for p in pairs), "存在非法条目（应恰好两字）"
    assert len({p[0] for p in pairs}) == len(pairs), "存在重复繁体字条目"
    assert kb.normalize("適合性評估與規定") == "适合性评估与规定"
    assert kb.normalize("客戶盡職審查") == "客户尽职审查"


def test_simplified_query_hits_traditional_corpus():
    """真实用户多打简体：简体提问必须能命中繁体语料。"""
    cn = kb.search("适当性 投资目标 建议", vertical="securities_suitability", top_k=3)
    hk = kb.search("適合性 投資目標 建議", vertical="securities_suitability", top_k=3)
    assert cn and hk
    assert cn[0]["id"] == hk[0]["id"] == "SFC-SUIT-01"


def test_mainland_term_maps_to_hk_term():
    """内地惯用词必须能命中香港术语语料（这是真实用户的输入习惯）。"""
    assert kb.normalize("适当性") == "适合性"
    hits = kb.search("适当性", vertical="securities_suitability", top_k=3)
    assert hits and hits[0]["id"] == "SFC-SUIT-01"
    # 「適當保安措施」这类词形相近但语义不同，不能被术语归一误伤
    assert kb.normalize("適當保安措施") == "适当保安措施"


def test_kb_endpoint_and_mcp_tool():
    r = client.post("/v1/kb/search", json={"query": "客戶盡職審查 實益擁有人", "vertical": "trust"})
    assert r.status_code == 200
    assert r.json()["clauses"]
    tools = {t["name"] for t in client.get("/v1/mcp/tools").json()["tools"]}
    assert {"ceron.kb_search", "ceron.agent_chat"} <= tools


# ---------------- Agent 闭环 ----------------
def test_agent_chat_cites_regulation():
    r = client.post("/v1/agent/chat", json={
        "message": "证券适当性方面有什么监管规定？", "vertical": "securities_suitability"})
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] and body["answer"]
    assert body["steps"] >= 1
    assert [t["tool"] for t in body["tool_calls"]]
    assert body["citations"], "回答必须附监管引用"
    assert any(c["source"] for c in body["citations"])
    assert body["trace_summary"]["steps"] >= 1


def test_agent_rule_lookup_path():
    r = client.post("/v1/agent/chat", json={
        "message": "按揭业务会触发哪些规则？", "vertical": "banking_mortgage"})
    assert r.status_code == 200
    body = r.json()
    assert any(t["tool"] == "rule_lookup" for t in body["tool_calls"])
    obs = " ".join(t["result_summary"] for t in body["tool_calls"])
    assert "rule_pack=" in obs


def test_agent_decide_path_uses_extracted_context():
    r = client.post("/v1/agent/chat", json={
        "message": "帮我评估一下这笔申请的结论",
        "vertical": "insurance_hk",
        "extracted": {"保单号": "P-1", "保额港币万": 100, "理赔金额港币万": 95},
    })
    assert r.status_code == 200
    body = r.json()
    assert any(t["tool"] == "decide" for t in body["tool_calls"])
    assert body["answer"]


def test_agent_multi_turn_remembers_vertical():
    first = client.post("/v1/agent/chat", json={
        "message": "按揭的监管依据是什么？", "vertical": "banking_mortgage"}).json()
    sid = first["session_id"]
    # 第二轮既不传 vertical 也不传 extracted，Agent 应沿用会话上下文
    second = client.post("/v1/agent/chat", json={
        "session_id": sid, "message": "那资金来源呢？"}).json()
    assert second["session_id"] == sid
    assert second["vertical"] == "banking_mortgage"


def test_agent_session_history_and_delete():
    r = client.post("/v1/agent/chat", json={"message": "我需要有哪些能力？"}).json()
    sid = r["session_id"]
    hist = client.get(f"/v1/agent/session/{sid}").json()["messages"]
    assert hist and hist[-1]["role"] == "assistant"
    assert client.delete(f"/v1/agent/session/{sid}").json()["ok"] is True
    assert client.get(f"/v1/agent/session/{sid}").status_code == 404
    assert agent.get_session(sid) is None


def test_agent_tool_failure_is_reported_not_fabricated():
    """未知工具 / 工具异常时，Agent 必须说失败，而不是编答案。"""
    out = agent.call_tool_local("kaput_tool", {}, "zh-HK")
    assert out.get("error")
    summary = agent._summarize("kaput_tool", out)
    assert summary.startswith("ERROR:")


@pytest.mark.anyio
async def test_llm_planner_falls_back_to_heuristic_when_mock():
    """mock（无密钥）时 LLMClient.chat 返回 None → 规划器必须回退确定性路由。"""
    from app.llm import LLMClient
    plan = await agent._llm_plan(LLMClient(None), [], "适当性规定？", {"vertical": "securities_suitability"})
    assert plan is None  # LLM 不可用 → 由 heuristic 接管
    fallback = agent._heuristic_plan("适当性规定？", {"vertical": "securities_suitability"})
    assert fallback["tool"] == "kb_search"
