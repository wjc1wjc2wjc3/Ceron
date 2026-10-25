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


# 标签与冒号之间允许少量修饰字符（如「成员姓名或实体名称：」「物业估值港币万：」）
_GAP = r"[^:：\n]{0,8}"
_VAL = r"[\u4e00-\u9fa5A-Za-z0-9（）()。.,・\- ]+"


def _field(text: str, label: str):
    m = re.search(label + _GAP + r"\s*[:：]\s*(" + _VAL + r")\s*$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(label + _GAP + r"\s*[:：]\s*(" + _VAL + r")", text)
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
    ("保额", "保额港币万"), ("保額", "保额港币万"), ("Sum Assured", "保额港币万"),
    ("年缴保费", "年缴保费港币万"), ("年繳保費", "年缴保费港币万"),
    ("Annual Premium", "年缴保费港币万"),
    ("理赔金额", "理赔金额港币万"), ("理賠金額", "理赔金额港币万"),
    ("Claim Amount", "理赔金额港币万"),
    ("KYC状态", "KYC状态"), ("KYC狀態", "KYC状态"), ("KYC Status", "KYC状态"),

    # ---- 银行按揭（HKMA）----
    ("申请人", "申请人"), ("物业估值", "物业估值港币万"), ("貸款金額", "贷款金额港币万"),
    ("贷款金额", "贷款金额港币万"), ("贷款成数LTV", "贷款成数LTV"), ("貸款成數LTV", "贷款成数LTV"),
    ("LTV", "贷款成数LTV"), ("月收入", "月收入港币"), ("月負債供款", "月负债供款港币"),
    ("月负债供款", "月负债供款港币"), ("供款入息比率DSR", "供款入息比率DSR"),
    ("供款入息比率", "供款入息比率DSR"), ("DSR", "供款入息比率DSR"), ("月供款", "月负债供款港币"),
    ("物业类型", "物业类型"), ("物業類型", "物业类型"), ("Property Type", "物业类型"),
    ("首期资金来源", "首期资金来源"), ("首期資金來源", "首期资金来源"),
    ("Down-payment Source", "首期资金来源"),

    # ---- 证券合适性（SFC）----
    ("风险承受度", "风险承受度"), ("風險承受度", "风险承受度"), ("Risk Tolerance", "风险承受度"),
    ("产品风险等级", "产品风险等级"), ("產品風險等級", "产品风险等级"), ("Product Risk", "产品风险等级"),
    ("投资经验年", "投资经验年"), ("投資經驗年", "投资经验年"),
    ("Investment Experience", "投资经验年"),
    ("财务状况", "财务状况港币"), ("財務狀況", "财务状况港币"), ("Financial Situation", "财务状况港币"),
    ("投资知识水平", "投资知识水平"), ("投資知識水平", "投资知识水平"),
    ("Knowledge Level", "投资知识水平"),
    ("产品类型", "产品类型"), ("產品類型", "产品类型"), ("Product Type", "产品类型"),

    # ---- 强积金（MPFA）----
    ("成员姓名", "成员姓名或实体名称"), ("成員姓名", "成员姓名或实体名称"), ("Member", "成员姓名或实体名称"),
    ("计划类型", "计划类型"), ("計劃類型", "计划类型"), ("Scheme", "计划类型"),
    ("雇主名称", "雇主名称"), ("僱主名稱", "雇主名称"), ("Employer", "雇主名称"),
    ("雇员状态", "雇员状态"), ("僱員狀態", "雇员状态"), ("Employment", "雇员状态"),
    ("雇主登记状态", "雇主登记状态"), ("僱主登記狀態", "雇主登记状态"),
    ("Employer Registration", "雇主登记状态"),
    ("供款状态", "供款状态"), ("供款狀態", "供款状态"), ("Contribution", "供款状态"),
    ("自愿供款", "自愿供款"), ("自願供款", "自愿供款"), ("Voluntary", "自愿供款"),

    # ---- 基金 OFC / LPF（SFC Type 9）----
    ("基金名称", "基金名称或实体名称"), ("基金名稱", "基金名称或实体名称"), ("Fund", "基金名称或实体名称"),
    ("结构类型", "结构类型"), ("結構類型", "结构类型"), ("Structure", "结构类型"),
    ("是否获证监会认可", "是否获证监会认可"), ("是否獲證監會認可", "是否获证监会认可"),
    ("SFC Authorized", "是否获证监会认可"),
    ("管理公司", "管理公司"), ("Manager", "管理公司"),
    ("投资者类型", "投资者类型"), ("投資者類型", "投资者类型"), ("Investor Type", "投资者类型"),
    ("募资规模", "募资规模港币万"), ("募資規模", "募资规模港币万"), ("Raise", "募资规模港币万"),
    ("资产规模", "资产规模港币万"), ("資產規模", "资产规模港币万"),
]

# 需要转成数值的字段（正则兜底也要给出强类型，便于规则包比较大小）
_FLOAT_FIELDS = {
    "物业估值港币万", "贷款金额港币万", "贷款成数LTV", "月收入港币", "月负债供款港币",
    "供款入息比率DSR", "投资经验年", "财务状况港币", "募资规模港币万", "资产规模港币万",
    "保额港币万", "年缴保费港币万", "理赔金额港币万",
}
_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_CURRENCY_RAW = re.compile(r"(港币|港幣|港元|HKD|USD|元)")   # 以「元」计价的原始金额
_WAN_UNIT = re.compile(r"(万|萬)")


def _to_float(val: str, key: str) -> float | None:
    """把捕获到的字符串转成数值；以「万元」为单位的字段会把裸货币金额换算成万。"""
    m = _NUM.search(val)
    if not m:
        return None
    try:
        num = float(m.group(0).replace(",", ""))
    except ValueError:
        return None
    # 字段名以「港币万」结尾（如 HKD 200,000 → 20 万）
    if key.endswith("港币万") and _CURRENCY_RAW.search(val) and not _WAN_UNIT.search(val):
        num = num / 10000.0
    return num


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
    # 配置化 schema 的字段名/别名（schema_config）追加在最后：内置标签优先命中，
    # 配置只补充新增字段与别名（自定义数据模型在无 LLM 时也能被正则兜底抽到）。
    try:
        from app.schema_config import extra_labels
        labels = _LABELS + extra_labels()
    except Exception:
        labels = _LABELS
    for label, key in labels:
        if key in out:          # 先命中者优先：避免宽泛别名（如 LTV）覆盖精确标签
            continue
        val = _field(text, label)
        if not val:
            continue
        if key in _FLOAT_FIELDS:
            num = _to_float(val, key)
            if num is None:
                continue
            val = num
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
