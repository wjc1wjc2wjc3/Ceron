"""法规速检知识库（RAG）：为 Agent 回答与审计包提供**可引用的监管依据出处**。

设计取舍（与全仓库一致的「离线可跑、绝不中断」哲学）：
- 语料：``data/regulations.json``（团队内部摘要/工作底稿，**非官方法规原文**），
  可用 ``REGULATIONS_PATH`` 覆盖；
- 检索：默认**确定性词项打分**（CJK 二元组 + 拉丁词，轻量 BM25），无需任何外部服务，
  结果可复现、可写进审计包（这一点对监管场景比向量相似度更重要）；
- 每条 clause 带 ``source`` / ``id`` / ``gates`` / ``verticals``，既能被 Agent 引用，
  也能按业务线、按监管闸口过滤。

正式合规判断请对照监管机构官方文本——本模块只负责「快速定位到该看哪一条」。
"""
import json
import os
import re
import threading
from typing import Optional

from app.config import settings

_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN = re.compile(r"[a-zA-Z][a-zA-Z0-9\-\.]+")

# 简繁归一化表：把繁体字映射到简体后再分词，使「适当性」与「適合性」能互相命中。
# 用一张静态表而非引入 opencc 依赖——覆盖本语料与常见合规词汇即可，
# 未收录的字原样放行（无害），保持零外部依赖、离线可跑。
# 每个条目是「繁体字+简体字」两字一组，用空白分隔。
# 不用两条长字符串逐位对齐（那种写法一旦错位会让整张表失效且难以察觉）。
_T2S_PAIRS = (
    "適适 規规 當当 監监 條条 實实 盡尽 擁拥 護护 戶户 "
    "業业 務务 權权 險险 貸贷 財财 產产 組组 織织 機机 "
    "構构 關关 係系 個个 們们 認认 識识 評评 報报 單单 "
    "並并 須须 採采 進进 處处 裡里 內内 後后 與与 擬拟 "
    "託托 資资 來来 時时 應应 為为 書书 強强 積积 僱雇 "
    "員员 義义 職职 還还 選选 終终 環环 結结 凍冻 視视 "
    "測测 證证 續续 紀纪 錄录 備备 辦办 轉转 讓让 載载 "
    "輸输 運运 達达 違违 銀银 錢钱 額额 預预 題题 顯显 "
    "體体 點点 龍龙 審审 際际 總总 歷历 將将 帶带 幫帮 "
    "對对 專专 從从 會会 華华 發发 現现 國国 經经 營营 "
    "統统 計计 較较 車车 邊边 遞递 過过 遊游 遠远 醫医 "
    "藥药 鐵铁 開开 閉闭 間间 門门 隊队 階阶 隨随 靜静 "
    "頭头 類类 願愿 飲饮 養养 館馆 驗验 驚惊 學学 習习 "
    "說说 話话 請请 誰谁 謝谢 語语 讀读 訴诉 談谈 詞词 "
    "標标 樣样 難难 區区 壓压 買买 賣卖 費费 貨货 責责 "
    "質质 這这 連连 週周 變变 寶宝 雲云 電电 損损 傷伤 "
    "裝装 訂订 親亲 檢检 歸归 斷断 麗丽 齒齿 齡龄"
)
_T2S_TABLE = str.maketrans(dict((p[0], p[1]) for p in _T2S_PAIRS.split()))


# 术语归一：内地惯用词 → 香港/本语料用词（多字词组优先，避免误伤「適當保安措施」
# 这类词形相近但语义不同的常见搭配）。只收录高频且会造成漏检的术语。
_TERMS: tuple = (
    ("适当性", "适合性"),    # 内地「适当性」= 香港「適合性」suitability
    ("适切性", "适合性"),
    ("尽调", "尽职审查"),    # 内地简写
    ("反洗钱", "打击洗钱"),
    ("制裁名单筛查", "制裁名单"),
)


def normalize(text: str) -> str:
    """简繁归一 + 术语归一，使两种中文输入收敛到同一套词条。"""
    s = (text or "").translate(_T2S_TABLE)
    for src, dst in _TERMS:
        s = s.replace(src, dst)
    return s

_CACHE: dict = {"mtime": None, "clauses": [], "df": {}}
_LOCK = threading.Lock()


def corpus_path() -> str:
    return settings.regulations_path or os.path.join("data", "regulations.json")


def load_clauses() -> list[dict]:
    """读取语料（按 mtime 热加载）；缺失/损坏返回空列表，不影响调用方。"""
    path = corpus_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []
    with _LOCK:
        if _CACHE["mtime"] == mtime:
            return _CACHE["clauses"]
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        clauses = [c for c in data.get("clauses", []) if isinstance(c, dict) and c.get("id")]
        _CACHE["mtime"] = mtime
        _CACHE["clauses"] = clauses
        _CACHE["df"] = _df(clauses)
    return _CACHE["clauses"]


def tokenize(text: str, title_weight: int = 1) -> list[str]:
    """中英混排分词：拉丁词小写 + CJK 字符二元组（标题可加权重复）。

    分词前先做简繁归一，使繁体语料能被简体提问命中（反之亦然）。
    """
    text = normalize(text)
    toks: list[str] = []
    for m in _LATIN.finditer(text):
        toks.append(m.group(0).lower())
    cjk = "".join(_CJK.findall(text))
    if len(cjk) == 1:
        toks.append(cjk)
    else:
        toks += [cjk[i:i + 2] for i in range(len(cjk) - 1)]
    return toks * max(1, title_weight)


def _df(clauses: list[dict]) -> dict:
    """文档频率（用于 IDF）；标题按 2 倍权重计入。"""
    df: dict = {}
    for c in clauses:
        seen = set(tokenize(f"{c.get('title','')}", title_weight=2) +
                   tokenize(f"{c.get('text','')} {c.get('en','')}"))
        for t in seen:
            df[t] = df.get(t, 0) + 1
    return df


def _clause_tokens(c: dict) -> list[str]:
    return tokenize(str(c.get("title", "")), title_weight=2) + \
        tokenize(f"{c.get('text','')} {c.get('en','')} {c.get('source','')}")


def search(query: str, top_k: int = 3, vertical: Optional[str] = None,
           gate: Optional[str] = None) -> list[dict]:
    """检索法规 clause，返回带 ``score`` 与引用信息的结果列表。"""
    clauses = load_clauses()
    if not clauses or not query:
        return []
    import math

    df = _CACHE["df"] or _df(clauses)
    n = max(1, len(clauses))
    q_tokens = set(tokenize(query))
    out: list[dict] = []
    for c in clauses:
        verticals = c.get("verticals") or []
        if vertical and "*" not in verticals and vertical not in verticals:
            continue
        if gate and gate not in (c.get("gates") or []):
            continue
        toks = _clause_tokens(c)
        if not toks:
            continue
        tf: dict = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for qt in q_tokens:
            if qt not in tf:
                continue
            idf = math.log((n + 1) / (1 + df.get(qt, 0))) + 1
            score += idf * (tf[qt] / (tf[qt] + 1.5))
        if score <= 0:
            continue
        # 长度归一，避免长条文天然占优
        score = score / math.sqrt(len(toks))
        out.append({
            "id": c.get("id"),
            "source": c.get("source"),
            "title": c.get("title"),
            "text": c.get("text"),
            "en": c.get("en"),
            "gates": c.get("gates") or [],
            "verticals": verticals,
            "score": round(score, 4),
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:max(1, top_k)]


def by_ids(ids: list[str]) -> list[dict]:
    """按 clause id 取原文（用于把引用渲染成可读列表）。"""
    clauses = load_clauses()
    want = set(ids or [])
    return [
        {"id": c["id"], "source": c.get("source"), "title": c.get("title"),
         "text": c.get("text"), "en": c.get("en")}
        for c in clauses if c["id"] in want
    ]


def count() -> int:
    return len(load_clauses())
