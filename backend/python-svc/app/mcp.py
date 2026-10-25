"""MCP（Model Context Protocol）工具层：把 Ceron 的抽取 / 富集 / 决策 / UBO 穿透
暴露成**任意 Agent 都能调用的工具**，而不是只服务自家前端。

借鉴邓白氏把企业数据做成 MCP、Docling 提供 MCP server 的做法：
客户自己的 Dify / n8n / Claude / 自研 Agent 可以直接调用 Ceron 的合规取证能力，
Ceron 从「一个系统」变成「能力供应商」。

这里实现最小可用的 JSON-RPC 2.0 契约：
- ``tools/list``：返回工具清单（OpenAI tool schema 形态的 inputSchema）；
- ``tools/call``：同步执行（抽取为 async，由调用方 await）。
"""
from typing import Any

from app import rules
from app.enrichment import enrich
from app.extraction import extract_document
from app.schemas import Vertical
from app.ubo import resolve as resolve_ubo

_LOC = {"type": "string", "enum": ["zh-HK", "en", "zh-CN"], "default": "zh-HK"}


def _vertical_schema() -> dict:
    return {"type": "string", "enum": [v.value for v in Vertical]}


def tools_list() -> list[dict]:
    return [
        {
            "name": "ceron.extract",
            "description": "从文档文本抽取业务线结构化字段（繁中/英文/简体混合）。",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "vertical": _vertical_schema(), "locale": _LOC},
                "required": ["text", "vertical"],
            },
        },
        {
            "name": "ceron.enrich",
            "description": "对已抽取字段跑外部数据取证（ICRIS/土地/信贷局/OFAC/HMT/CRS），失败自动降级。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "vertical": _vertical_schema(),
                    "extracted": {"type": "object"},
                    "locale": _LOC,
                },
                "required": ["vertical", "extracted"],
            },
        },
        {
            "name": "ceron.decide",
            "description": "跑合规闸口规则包，返回通过/拒绝/转人工 + 三语理由 + 规则命中记录。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "vertical": _vertical_schema(),
                    "extracted": {"type": "object"},
                    "enrichment": {"type": "object"},
                    "locale": _LOC,
                },
                "required": ["vertical", "extracted"],
            },
        },
        {
            "name": "ceron.ubo",
            "description": "按股权图穿透受益所有人（相乘计算有效持股，识别循环持股）。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "extracted": {"type": "object"},
                    "ownership_edges": {"type": "array", "items": {"type": "object"}},
                    "root": {"type": "string"},
                },
                "required": ["extracted"],
            },
        },
        {
            "name": "ceron.rules",
            "description": "导出当前生效的合规闸口规则包（可 diff、可交给合规审阅）。",
            "inputSchema": {"type": "object", "properties": {"version": {"type": "string"}}},
        },
        {
            "name": "ceron.kb_search",
            "description": "检索香港/国际监管依据条文（SFC/HKMA/MPFA/AMLO/PDPO），返回带 source 的可引用出处。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "vertical": {"type": "string"},
                    "gate": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        },
        {
            "name": "ceron.agent_chat",
            "description": "合规 Agent 对话（规划→工具调用→反思），返回带监管引用的回答；session_id 用于多轮记忆。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "session_id": {"type": "string"},
                    "vertical": {"type": "string"},
                    "extracted": {"type": "object"},
                    "locale": _LOC,
                },
                "required": ["message"],
            },
        },
    ]


async def call_tool(name: str, arguments: dict | None = None) -> dict:
    args = arguments or {}
    locale = args.get("locale", "zh-HK")

    if name == "ceron.extract":
        # vertical 接受内置枚举值或 schema 配置（SCHEMA_CONFIG）定义的自定义业务线
        out = await extract_document(args.get("text", ""), args["vertical"])
        return out

    if name == "ceron.enrich":
        return enrich(args["vertical"], args.get("extracted", {}), locale)

    if name == "ceron.decide":
        from app.decision import assess_with_review

        return assess_with_review(
            args["vertical"], args.get("extracted", {}), args.get("enrichment") or {}, locale
        )

    if name == "ceron.ubo":
        return resolve_ubo(args.get("extracted", {}), args.get("ownership_edges"), args.get("root"))

    if name == "ceron.rules":
        return rules.export(args.get("version"))

    if name == "ceron.kb_search":
        from app import kb
        return {"clauses": kb.search(args.get("query", ""), top_k=int(args.get("top_k") or 3),
                                     vertical=args.get("vertical"), gate=args.get("gate"))}

    if name == "ceron.agent_chat":
        from app import agent
        return await agent.chat(
            args.get("message", ""), session_id=args.get("session_id"),
            vertical=args.get("vertical"), extracted=args.get("extracted"), locale=locale,
        )

    raise KeyError(f"unknown tool: {name}")


async def handle_rpc(body: dict) -> dict:
    """最小 JSON-RPC 2.0 处理（tools/list 与 tools/call）。"""
    rid = body.get("id")
    method = body.get("method")
    try:
        if method == "tools/list":
            result: Any = {"tools": tools_list()}
        elif method == "tools/call":
            params = body.get("params") or {}
            out = await call_tool(params.get("name"), params.get("arguments") or {})
            result = {"content": [{"type": "text", "text": str(out)}], "structuredContent": out}
        else:
            return {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32601, "message": f"method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": rid, "result": result}
    except KeyError as e:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": str(e)}}
    except Exception as e:  # 工具内部异常：返回 RPC 错误，不抛出
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": str(e)[:300]}}
