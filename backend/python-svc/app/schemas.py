"""香港金融业抽取字段 Schema（全部可选，兼容模型漏抽与正则兜底）。

vertical=insurance_hk  : 港股保险承保/理赔
vertical=family_office: 家族办公室 / 信托 KYC-CDD
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Vertical(str, Enum):
    insurance_hk = "insurance_hk"
    family_office = "family_office"
    # —— 业务补充（路线图优先级 1，扩展承保/合规覆盖）——
    banking_mortgage = "banking_mortgage"          # 银行按揭承保（HKMA）
    securities_suitability = "securities_suitability"  # 证券合适性（SFC）
    mpf = "mpf"                                    # 强积金（MPFA）
    fund_ofc_lpf = "fund_ofc_lpf"                  # 基金/OFC/LPF/REIT（SFC Type 9）


class InsuranceHKApplication(BaseModel):
    保单号: Optional[str] = None
    投保人: Optional[str] = None
    受保人: Optional[str] = None
    受益人: Optional[str] = None
    险种: Optional[str] = None
    保额港币万: Optional[float] = None
    年缴保费港币万: Optional[float] = None
    理赔类型: Optional[str] = None
    理赔金额港币万: Optional[float] = None
    出险日期: Optional[str] = None
    资料完整度: Optional[float] = None
    KYC状态: Optional[str] = None


class FamilyOfficeProfile(BaseModel):
    客户姓名或实体名称: Optional[str] = None
    身份类型: Optional[str] = None            # 个人 / 公司 / 信托
    资产规模港币万: Optional[float] = None
    资产类别: Optional[str] = None
    资金来源: Optional[str] = None
    受益所有人: Optional[str] = None
    是否政治公众人物PEP: Optional[bool] = None
    风险等级: Optional[str] = None
    KYC状态: Optional[str] = None


class GenericProfile(BaseModel):
    """未知 / 新增业务线的通用兜底模型：不限制字段，LLM 自由抽取。"""

    model_config = {"extra": "allow"}

    客户姓名或实体名称: Optional[str] = None
    身份类型: Optional[str] = None
    资产规模港币万: Optional[float] = None
    资金来源: Optional[str] = None
    受益所有人: Optional[str] = None
    风险等级: Optional[str] = None
    KYC状态: Optional[str] = None


class BankingMortgageApplication(BaseModel):
    """银行按揭承保（HKMA 监管）：LTV / DSR / 还款能力 / 首期来源。"""
    申请人: Optional[str] = None
    物业估值港币万: Optional[float] = None
    贷款金额港币万: Optional[float] = None
    贷款成数LTV: Optional[float] = None          # 0~1，如 0.6
    月收入港币: Optional[float] = None
    月负债供款港币: Optional[float] = None
    供款入息比率DSR: Optional[float] = None       # 总供款/入息，0~1
    物业类型: Optional[str] = None               # 住宅 / 商用 / 工业
    首期资金来源: Optional[str] = None
    KYC状态: Optional[str] = None


class SecuritiesSuitabilityProfile(BaseModel):
    """证券合适性（SFC）：风险承受度 vs 产品风险、经验与知识。"""
    客户姓名或实体名称: Optional[str] = None
    风险承受度: Optional[str] = None             # 低 / 中 / 高
    产品风险等级: Optional[str] = None           # 低 / 中 / 高
    投资经验年: Optional[float] = None
    财务状况港币: Optional[float] = None
    投资知识水平: Optional[str] = None           # 低 / 中 / 高
    产品类型: Optional[str] = None               # 衍生品 / 基金 / 债券 / 股票
    KYC状态: Optional[str] = None


class MPFProfile(BaseModel):
    """强积金（MPFA）：雇主登记、雇员资格、供款合规。"""
    成员姓名或实体名称: Optional[str] = None
    计划类型: Optional[str] = None               # 强积金 / 职业退休
    雇主名称: Optional[str] = None
    雇员状态: Optional[str] = None               # 在职 / 自雇 / 失业
    雇主登记状态: Optional[str] = None           # 已登记 / 未登记
    供款状态: Optional[str] = None               # 正常 / 逾期 / 豁免
    自愿供款: Optional[str] = None
    KYC状态: Optional[str] = None


class FundOFCLPFProfile(BaseModel):
    """基金 / OFC / LPF / REIT（SFC Type 9）：结构、认可、受益所有权。"""
    基金名称或实体名称: Optional[str] = None
    结构类型: Optional[str] = None               # OFC / LPF / REIT / 信托 / 有限合伙
    是否获证监会认可: Optional[str] = None        # 是 / 否 / 不适用
    管理公司: Optional[str] = None
    投资者类型: Optional[str] = None             # 专业 / 零售
    受益所有人: Optional[str] = None
    募资规模港币万: Optional[float] = None
    KYC状态: Optional[str] = None


_SCHEMAS = {
    Vertical.insurance_hk: InsuranceHKApplication,
    Vertical.family_office: FamilyOfficeProfile,
    Vertical.banking_mortgage: BankingMortgageApplication,
    Vertical.securities_suitability: SecuritiesSuitabilityProfile,
    Vertical.mpf: MPFProfile,
    Vertical.fund_ofc_lpf: FundOFCLPFProfile,
}


def get_schema(vertical: Vertical):
    # 已知业务线用专属 schema；其余（含新增业务线）走通用兜底，保证流水线不中断。
    return _SCHEMAS.get(vertical, GenericProfile)
