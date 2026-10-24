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


_SCHEMAS = {
    Vertical.insurance_hk: InsuranceHKApplication,
    Vertical.family_office: FamilyOfficeProfile,
}


def get_schema(vertical: Vertical):
    # 已知业务线用专属 schema；其余（含新增业务线）走通用兜底，保证流水线不中断。
    return _SCHEMAS.get(vertical, GenericProfile)
