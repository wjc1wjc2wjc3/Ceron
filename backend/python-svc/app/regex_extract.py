"""中/繁/英正则兜底抽取：保证无 LLM 密钥时也能抽取关键香港金融字段。

覆盖：繁體中文、簡體中文、English 标签；金额支持「單位在後」（800萬）与
「貨幣在前」（HKD 8,000,000）两种书写。
"""
import re

_USCI = re.compile(r"[0-9A-HJ-NP-RTUWXY]{2}\d{6}[0-9A-HJ-NP-RTUWXY]{10}")
_ID = re.compile(r"\b\d{17}[\dXx]\b")
_CN_PHONE = re.compile(r"1[3-9]\d{9}")
_HK_PHONE = re.compile(r"(?:\+?852[-\s]?)?[569]\d{3}[-\s]?\d{4}")

# 单位在数字后（800萬 / 800万 / 800元）
_MONEY_SUFFIX = re.compile(r"([0-9][0-9,]{1,})\s*(港币|港幣|港元|HKD|萬元|万元|萬|万|元)")
# 货币在数字前（HKD 8,000,000 / 港元 8,000,000）
_MONEY_PREFIX = re.compile(r"(港币|港幣|港元|HKD)\s*([0-9][0-9,]{1,})")

_POLICY = re.compile(r"(?:保单号|保單號|Policy\s*(?:No|Number))\s*[:：]?\s*([A-Za-z0-9\-]+)")


def _field(text: str, label: str):
    m = re.search(label + r"\s*[:：]\s*([\u4e00-\u9fa5A-Za-z0-9（）()·\- ]+?)\s*$",
                  text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(label + r"\s*[:：]\s*([\u4e00-\u9fa5A-Za-z0-9（）()·\-]+)", text)
    return m.group(1) if m else None


# 标签 → 抽取字段（简繁/英文别名共用同一字段）
_LABELS = [
    ("投保人", "投保人"), ("Policyholder", "投保人"),
    ("受保人", "受保人"), ("Insured", "受保人"),
    ("受益人", "受益人"), ("Beneficiary", "受益人"),
    ("险种", "险种"), ("險種", "险种"), ("Product", "险种"), ("Plan", "险种"),
    ("客户姓名", "客户姓名或实体名称"), ("客戶姓名", "客户姓名或实体名称"),
    ("实体名称", "客户姓名或实体名称"), ("Applicant", "客户姓名或实体名称"),
    ("身份类型", "身份类型"), ("身份類型", "身份类型"),
    ("资产类别", "资产类别"), ("資產類別", "资产类别"),
    ("资金来源", "资金来源"), ("資金來源", "资金来源"), ("Source of Funds", "资金来源"),
    ("受益所有人", "受益所有人"), ("Beneficial Owner", "受益所有人"),
    ("风险等级", "风险等级"), ("風險等級", "风险等级"), ("Risk Level", "风险等级"),
    ("KYC状态", "KYC状态"), ("KYC狀態", "KYC状态"), ("KYC Status", "KYC状态"),
]


def _money_candidates(text: str):
    """按出现位置排序的金额候选（统一换算为「万」）。"""
    found = []  # (start, value_in_wan)
    for m in _MONEY_SUFFIX.finditer(text):
        num = float(m.group(1).replace(",", ""))
        unit = m.group(2)
        if unit in ("万元", "万", "萬元", "萬"):
            val = num
        elif unit in ("港币", "港幣", "港元", "HKD"):
            val = num / 10000.0
        else:  # 元
            val = num / 10000.0
        found.append((m.start(), val))
    for m in _MONEY_PREFIX.finditer(text):
        num = float(m.group(2).replace(",", ""))
        found.append((m.start(), num / 10000.0))  # HKD → 万
    found.sort(key=lambda x: x[0])
    return [v for _, v in found]


def rule_extract(text: str) -> dict:
    out: dict = {}
    for label, key in _LABELS:
        val = _field(text, label)
        if val:
            out[key] = val

    m = _POLICY.search(text)
    if m:
        out["保单号"] = m.group(1)

    cands = _money_candidates(text)
    if cands:
        out["_金额候选"] = cands

    m = _USCI.search(text)
    if m:
        out["统一社会信用代码"] = m.group(0)
    m = _ID.search(text)
    if m:
        out["身份证号"] = m.group(0)
    m = _HK_PHONE.search(text) or _CN_PHONE.search(text)
    if m:
        out["联系电话"] = m.group(0)

    if "政治公众人物" in text or "政治公眾人物" in text or "PEP" in text:
        if re.search(r"(PEP|政治公众人物|政治公眾人物)\s*[:：]?\s*(是|true|yes|Yes|TRUE)", text, re.IGNORECASE):
            out["是否政治公众人物PEP"] = True

    return out
