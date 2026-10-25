"""受益所有權（UBO）穿透：用**圖結構**取代逐層文本推理。

借鑒 Quantexa 的實體解析與 graphrag 的圖遍歷思路：
把股權關係建成有向圖，沿路徑**相乘**計算有效持股比例，識別最終自然人，
並能處理循環持股（cycle）——這是家辦與信託場景最常見的兩類難題。

輸入兩類：
1. 結構化股權邊 ``ownership_edges``：[{"from":"A","to":"B","pct":60}]（前端/API 可選傳入）；
2. 若無邊，則從抽取字段「受益所有人」退化解析（保守：只給出人選與比例，不做穿透）。
"""
from typing import Any

THRESHOLD = 0.25          # 常用申報門檻（FATF / 香港 AMLO 實務口徑）
MAX_DEPTH = 8

_ENTITY_HINTS = (
    "公司", "有限", "集團", "控股", "信託", "信托", "基金", "合伙", "合夥",
    "ltd", "limited", "llc", "inc", "holdings", "trust", "fund", "lp", "capital",
)


def _is_entity(name: str) -> bool:
    low = (name or "").lower()
    return any(h in low for h in _ENTITY_HINTS)


def _pct(v: Any) -> float:
    """把 60 / 0.6 / "60%" / "60" 統一到 0..1。"""
    if v is None:
        return 0.0
    if isinstance(v, str):
        v = v.strip().replace("%", "").replace("％", "")
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if f > 1:          # 60 -> 0.6
        f = f / 100.0
    return max(0.0, min(1.0, f))


def _parse_owners(raw: str) -> list[tuple[str, float]]:
    """從「受益所有人」文本退化解析：陳大文 60%、陳小文 40% / 陳大文、陳小文。"""
    out: list[tuple[str, float]] = []
    for part in [p for p in __import__("re").split(r"[、,，/;；]|及|和|and", raw or "") if p.strip()]:
        seg = part.strip()
        pct = 0.0
        import re as _re

        m = _re.search(r"(\d+(?:\.\d+)?)\s*[%％]", seg)
        if m:
            pct = _pct(m.group(1))
            seg = _re.sub(r"(\d+(?:\.\d+)?)\s*[%％]", "", seg).strip(" ：:（）()")
        if seg:
            out.append((seg, pct))
    return out


def resolve(
    extracted: dict,
    ownership_edges: list[dict] | None = None,
    root: str | None = None,
) -> dict:
    """計算受益所有人；返回圖、穿透路徑與未決標記。"""
    edges_raw = ownership_edges or []
    edges: list[dict] = []
    for e in edges_raw:
        if not isinstance(e, dict):
            continue
        src, dst, pct = (e.get("from") or "").strip(), (e.get("to") or "").strip(), _pct(e.get("pct"))
        if src and dst and pct > 0:
            edges.append({"from": src, "to": dst, "pct": pct})

    fallback_owners = _parse_owners(str(extracted.get("受益所有人") or ""))
    if not (root or "").strip():
        root = str(
            extracted.get("客户姓名或实体名称")
            or extracted.get("客户姓名")
            or extracted.get("成员姓名或实体名称")
            or extracted.get("基金名称或实体名称")
            or extracted.get("基金名称")
            or extracted.get("申请人")
            or extracted.get("投保人")
            or extracted.get("公司名称")
            or ""
        )
    root = (root or "").strip()

    nodes: dict[str, str] = {}
    for e in edges:
        nodes.setdefault(e["from"], "entity" if _is_entity(e["from"]) else "person")
        nodes.setdefault(e["to"], "entity" if _is_entity(e["to"]) else "person")
    for name, _ in fallback_owners:
        nodes.setdefault(name, "entity" if _is_entity(name) else "person")

    beneficial: list[dict] = []
    cycles: list[list[str]] = []

    if edges and root:
        # 沿持股鏈相乘，取每個終端的最大有效持股比例
        best: dict[str, tuple[float, list[str]]] = {}
        adj: dict[str, list[tuple[str, float]]] = {}
        for e in edges:
            adj.setdefault(e["from"], []).append((e["to"], e["pct"]))

        def walk(cur: str, acc: float, path: list[str], depth: int) -> None:
            if depth > MAX_DEPTH:
                return
            for nxt, pct in adj.get(cur, []):
                if nxt in path:                    # 循環持股：記錄後停止，避免無窮遞歸
                    cycles.append(path + [nxt])
                    continue
                eff = acc * pct
                prev = best.get(nxt)
                if prev is None or eff > prev[0]:
                    best[nxt] = (eff, path + [nxt])
                walk(nxt, eff, path + [nxt], depth + 1)

        walk(root, 1.0, [root], 1)
        for name, (eff, path) in best.items():
            beneficial.append({
                "name": name,
                "pct": round(eff, 4),
                "path": path,
                "type": nodes.get(name, "person" if not _is_entity(name) else "entity"),
                "above_threshold": eff >= THRESHOLD,
            })
        beneficial.sort(key=lambda x: -x["pct"])

    # 無結構化邊時：退回文本解析（單層，標記為未穿透）
    if not beneficial and fallback_owners:
        for name, pct in fallback_owners:
            beneficial.append({
                "name": name,
                "pct": round(pct, 4) if pct else None,
                "path": [root or "root", name] if root else [name],
                "type": nodes.get(name, "person" if not _is_entity(name) else "entity"),
                "above_threshold": (pct >= THRESHOLD) if pct else None,
            })

    unresolved = not beneficial or all(
        (b["pct"] is None) or (b["pct"] < THRESHOLD) for b in beneficial
    )

    return {
        "threshold": THRESHOLD,
        "root": root or None,
        "nodes": [{"name": n, "type": t} for n, t in nodes.items()],
        "edges": edges,
        "beneficial_owners": beneficial,
        "cycles": cycles,
        "unresolved": unresolved,
        "mode": "graph" if edges else "fallback",
    }
