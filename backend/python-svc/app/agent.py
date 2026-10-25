"""合规 Agent：把 Ceron 从「流水线」升级为「规划 → 工具调用 → 反思」的闭环。

设计原则（与全仓库一致）：
- **规则引擎仍是最终裁决方**，LLM 只做「取证、提问、解释」——Agent 可以很聪明，
  但决策口径必须可复现、可审计；所以每次工具调用都进 trace，回答必须附引用出处。
- **无 LLM 也能跑**：规划器在 mock/无密钥时回退到确定性意图路由，
  回答由模板拼装，绝不因模型不可用而中断。
- **会话记忆**：``SESSIONS`` 保存多轮上下文（按 session_id），供追问
  （「那她的资金来源呢？」这种省略主语的追问必须有上下文才答得对）。

闭环伪代码::

    for step in range(max_steps):
        decision = plan(context)          # LLM 或确定性路由
        if decision.final: break
        observation = call(decision.tool) # kb_search / decide / rule_lookup / capabilities
        context += observation            # 反思：把观察结果喂回下一轮规划
    answer = compose(context)             # 带 citations
"""
import json
import re
import time
import uuid
from typing import Optional

from app import kb, rules
from app.llm import LLMClient
from app.trace import new_trace, stamp, summary

MAX_STEPS = 4          # 防止无限循环：最多 4 次工具调用
HISTORY_LIMIT = 12     # 会话记忆窗口（消息条数，含工具观察）
MAX_SESSIONS = 200     # 进程内 session 上限，超出淘汰最旧（防内存增长）

SESSIONS: dict[str, list[dict]] = {}
# 每个会话的「工作上下文」（业务线/抽取数据）：多轮追问不会重复传参，
# 例如「那她的资金来源呢？」需要沿用上一轮的 vertical 与 extracted。
_SESSION_CTX: dict[str, dict] = {}


# ==================== 工具层 ====================
def tool_schemas() -> list[dict]:
    """OpenAI tool schema 形态的工具清单（供 LLM 规划器与 MCP 复用同一份契约）。"""
    return [
        {
            "name": "kb_search",
            "description": "检索香港/国际监管依據条文（SFC / HKMA / MPFA / AMLO / PDPO），返回可引用出处。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词"},
                    "vertical": {"type": "string"},
                    "gate": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        },
        {
            "name": "rule_lookup",
            "description": "查询当前生效的合规闸口规则包（不跑分），用于回答「哪些规则会触发」。",
            "parameters": {
                "type": "object",
                "properties": {"vertical": {"type": "string"}, "gate": {"type": "string"}},
            },
        },
        {
            "name": "decide",
            "description": "对已抽取字段跑合规闸口规则包，输出通过/拒绝/转人工 + 理由 + 规则命中。",
            "parameters": {
                "type": "object",
                "properties": {
                    "vertical": {"type": "string"},
                    "extracted": {"type": "object"},
                    "enrichment": {"type": "object"},
                },
                "required": ["vertical", "extracted"],
            },
        },
        {
            "name": "capabilities",
            "description": "查询平台覆盖度（业务线/数据源/规则数/解析器），回答「你们支持什么」。",
            "parameters": {"type": "object", "properties": {}},
        },
    ]


def call_tool_local(name: str, args: dict, locale: str = "zh-HK",
                    trace: Optional[list] = None) -> dict:
    """同步执行工具（异常一律转成 observation，不抛出，保证闭环继续）。"""
    t0 = time.perf_counter()
    try:
        if name == "kb_search":
            out = {"clauses": kb.search(
                args.get("query", ""),
                top_k=int(args.get("top_k") or 3),
                vertical=args.get("vertical"),
                gate=args.get("gate"),
            )}
        elif name == "rule_lookup":
            pack = rules.export()
            vertical = args.get("vertical")
            gate = args.get("gate")
            items = pack["rules"]
            if vertical:
                items = [r for r in items if r["vertical"] in ("*", vertical)]
            if gate:
                items = [r for r in items if r["gate"] == gate]
            out = {"rule_pack_version": pack["version"], "count": len(items), "rules": items[:10]}
        elif name == "decide":
            from app.decision import assess_with_review
            out = assess_with_review(
                args.get("vertical", "insurance_hk"),
                args.get("extracted", {}),
                args.get("enrichment") or {},
                locale,
                trace=trace,
            )
        elif name == "capabilities":
            from app.capabilities import snapshot
            out = snapshot(locale)
        else:
            out = {"error": f"unknown tool: {name}"}
    except Exception as e:  # 工具失败也要让 Agent 能解释「为什么答不出来」
        out = {"error": str(e)[:300]}
    stamp(trace, "agent_tool", name, started=t0, ok=not bool(out.get("error")),
          args_summary=str(args)[:200])
    return out


# ==================== 会话记忆 ====================
def new_session() -> str:
    sid = f"s-{uuid.uuid4().hex[:12]}"
    SESSIONS[sid] = []
    _evict()
    return sid


def _evict() -> None:
    if len(SESSIONS) > MAX_SESSIONS:
        for k in list(SESSIONS)[:len(SESSIONS) - MAX_SESSIONS]:
            SESSIONS.pop(k, None)


def get_session(sid: str) -> Optional[list[dict]]:
    return SESSIONS.get(sid)


def delete_session(sid: str) -> bool:
    _SESSION_CTX.pop(sid, None)
    return SESSIONS.pop(sid, None) is not None


# ==================== 规划器 ====================
_HINT_INTENT = [
    # (正则, 工具, 取参函数)
    (r"規定|法規|條例|監管|依法|合規依據|適當性|適合性|了解|citation|regulation|requirement",
     "kb_search", lambda q, ctx: {"query": q}),
    (r"規則|触发|閘口|rule", "rule_lookup", None),
    (r"决策|決定|评估|审批|要不要|decide", "decide", None),
    (r"支持|覆盖|能力|有哪些|capabilit", "capabilities", None),
]


def _heuristic_plan(message: str, ctx: dict) -> dict:
    """确定性意图路由（无 LLM 时的规划器）。"""
    for pattern, tool, mk in _HINT_INTENT:
        if re.search(pattern, message, re.I):
            if tool == "decide" and not ctx.get("extracted"):
                continue  # 没有抽取数据就别硬跑决策
            args = mk(message, ctx) if mk else {"vertical": ctx.get("vertical")}
            if tool in ("kb_search",) and ctx.get("vertical"):
                args.setdefault("vertical", ctx["vertical"])
            return {"action": "tool", "tool": tool, "args": args}
    # 默认：先检索法规（大多数合规问题都值得先看依据）
    args = {"query": message}
    if ctx.get("vertical"):
        args["vertical"] = ctx["vertical"]
    return {"action": "tool", "tool": "kb_search", "args": args}


async def _llm_plan(client: LLMClient, history: list[dict], message: str, ctx: dict,
                    trace: Optional[list] = None) -> Optional[dict]:
    """LLM 规划器：输出下一步该调哪个工具，或直接给最终答案。"""
    schemas = tool_schemas()
    sys = (
        "你是 Ceron 合规 Agent 的规划器。根据对话历史与用户问题，"
        "从下列工具中选择下一步动作。严格输出 JSON："
        '{"action":"tool","tool":"<name>","args":{...}} 或 {"action":"final","answer":"<回答>"}。'
        "不要输出多余文字。工具清单：\n" + json.dumps(schemas, ensure_ascii=False)
    )
    convo = "\n".join(
        f"{m['role']}: {str(m.get('content'))[:800]}" for m in history[-6:]
    )
    prompt = (
        f"对话历史:\n{convo}\n\n用户问题: {message}\n"
        f"已知上下文: vertical={ctx.get('vertical')}, extracted={'有' if ctx.get('extracted') else '无'}\n"
        "下一步 JSON:"
    )
    raw = await client.chat(prompt, sys, trace=trace, want_json=True)
    return _parse_plan(raw)


def _parse_plan(raw: Optional[str]) -> Optional[dict]:
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        plan = json.loads(m.group(0))
        if plan.get("action") == "final" and plan.get("answer"):
            return {"action": "final", "answer": str(plan["answer"])}
        if plan.get("action") == "tool" and plan.get("tool") in {t["name"] for t in tool_schemas()}:
            return {"action": "tool", "tool": plan["tool"], "args": plan.get("args") or {}}
    except Exception:
        pass
    return None


# ==================== 主闭环 ====================
async def chat(message: str, session_id: Optional[str] = None, vertical: Optional[str] = None,
               extracted: Optional[dict] = None, locale: str = "zh-HK",
               cfg=None, trace: Optional[list] = None) -> dict:
    """跑一轮「规划 → 工具调用 → 反思」，返回带引用与工具轨迹的回答。"""
    trace = trace if trace is not None else new_trace()
    sid = session_id or new_session()
    history = SESSIONS.setdefault(sid, [])
    _evict()
    client = LLMClient(cfg)

    prev_ctx = _SESSION_CTX.get(sid, {})
    vkey = vertical or prev_ctx.get("vertical")
    ex = extracted if isinstance(extracted, dict) and extracted else prev_ctx.get("extracted") or {}
    ctx = {"vertical": vkey, "extracted": ex}
    _SESSION_CTX[sid] = {"vertical": vkey, "extracted": ex}

    citations: list[dict] = []
    tool_calls: list[dict] = []
    steps = 0
    answer = ""

    for step in range(MAX_STEPS):
        plan = await _llm_plan(client, history, message, ctx, trace=trace) if step == 0 else None
        if plan is None:
            plan = _heuristic_plan(message, ctx) if steps == 0 else {"action": "final", "answer": ""}
        if plan.get("action") == "final":
            answer = plan.get("answer") or ""
            break

        name, args = plan["tool"], plan.get("args") or {}
        observation = call_tool_local(name, args, locale, trace=trace)
        steps += 1
        tool_calls.append({"tool": name, "args": args, "result_summary": _summarize(name, observation)})

        # 反思：把观察写回上下文，下一轮规划会看到（这是「Agent」而非单次调用的关键）
        history.append({"role": "tool", "tool": name, "content": _summarize(name, observation)})
        for c in observation.get("clauses", []):
            citations.append({k: c.get(k) for k in ("id", "source", "title", "text")})
        if observation.get("error"):
            # 工具失败：让 Agent 明确说出来，而不是编造答案
            answer = f"（工具 {name} 执行失败：{observation['error']}）"
            break

    if not answer:
        llm_answer = await _llm_compose(client, message, tool_calls, citations, locale, trace=trace)
        answer = llm_answer or _template_answer(tool_calls, citations, locale)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer, "citations": citations})
    SESSIONS[sid] = history[-HISTORY_LIMIT:]

    # 引用去重（保留首次出现顺序）
    seen, uniq = set(), []
    for c in citations:
        if c.get("id") and c["id"] not in seen:
            seen.add(c["id"])
            uniq.append(c)

    return {
        "session_id": sid,
        "answer": answer,
        "citations": uniq,
        "tool_calls": tool_calls,
        "steps": steps,
        "locale": locale,
        "vertical": ctx.get("vertical"),
        "trace": trace,
        "trace_summary": summary(trace),
    }


def _summarize(tool: str, observation: dict) -> str:
    """把工具结果压成一两句话喂回规划器（控制上下文长度）。"""
    if observation.get("error"):
        return f"ERROR: {observation['error']}"
    if tool == "kb_search":
        cls = observation.get("clauses") or []
        if not cls:
            return "kb_search: 无命中 regulation clause"
        return "kb_search 命中: " + "; ".join(
            f"[{c.get('id')}] {c.get('title')} ({c.get('source')})" for c in cls)
    if tool == "rule_lookup":
        return (f"rule_lookup: rule_pack={observation.get('rule_pack_version')}, "
                f"{observation.get('count')} 条规则")
    if tool == "decide":
        return (f"decide: action={observation.get('action')}, score={observation.get('risk_score')}, "
                f"review_level={observation.get('review_level')}, reasons={observation.get('reasons')}")
    if tool == "capabilities":
        return (f"capabilities: verticals={observation.get('verticals', {}).get('count')}, "
                f"data_sources={observation.get('data_sources', {}).get('implemented')}, "
                f"rules={observation.get('rules', {}).get('count')}")
    return f"{tool}: {str(observation)[:200]}"


async def _llm_compose(client: LLMClient, message: str, tool_calls: list[dict],
                       citations: list[dict], locale: str,
                       trace: Optional[list] = None) -> Optional[str]:
    """用 LLM 把工具观察组织成自然语言回答（要求列出引用 id）。"""
    cites = "\n".join(f"[{c.get('id')}] {c.get('source')} {c.get('title')}: {c.get('text')}"
                      for c in citations[:6])
    obs = "\n".join(t.get("result_summary", "") for t in tool_calls)
    sys = ("你是 Ceron 合规 Agent。根据工具观察作答，必须引用方括号内编号的监管依据。"
           f"使用语言: {locale}。不要编造工具未给出的信息。")
    prompt = f"用户问题: {message}\n\n工具观察:\n{obs}\n\n监管依据:\n{cites}\n\n回答:"
    return await client.chat(prompt, sys, trace=trace)


def _template_answer(tool_calls: list[dict], citations: list[dict], locale: str) -> str:
    """无 LLM 时的确定性回答模板（保证「永远有答案」）。"""
    if not tool_calls:
        return {"zh-HK": "未调用任何工具即可作答：请提供更具体的合规问题。",
                "en": "Provide a more specific compliance question.",
                "zh-CN": "未调用任何工具即可作答：请提供更具体的合规问题。"}.get(locale, "")
    obs = "\n".join(f"- {t.get('result_summary','')}" for t in tool_calls)
    if not citations:
        return f"已执行工具并得到以下结论：\n{obs}"
    cite_list = "\n".join(f"- [{c.get('id')}] {c.get('source')}《{c.get('title')}》：{c.get('text')}"
                          for c in citations[:5])
    head = {"zh-HK": "依据如下（摘要为内部工作底稿，正式判断请对照监管原文）：\n",
            "en": "Grounding (internal working summary; verify against official text):\n",
            "zh-CN": "依据如下（摘要为内部工作底稿，正式判断请对照监管原文）：\n"}.get(locale, "")
    return f"{head}{cite_list}\n\n佐证：\n{obs}"
