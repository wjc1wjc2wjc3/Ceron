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


_SCHEMAS = {
    Vertical.insurance_hk: InsuranceHKApplication,
    Vertical.family_office: FamilyOfficeProfile,
}


def get_schema(vertical: Vertical):
    return _SCHEMAS[vertical]
