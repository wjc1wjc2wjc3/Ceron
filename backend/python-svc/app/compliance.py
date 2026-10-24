"""香港合规层：个人/企业敏感信息脱敏 + 数据驻留校验（对应 PDPO）。"""
import re

from app.config import settings

_ID_CARD = re.compile(r"\b\d{17}[\dXx]\b")
_PHONE = re.compile(r"1[3-9]\d{9}")
_HK_PHONE = re.compile(r"(?:\+?852[-\s]?)?[569]\d{3}[-\s]?\d{4}")
_BANK_CARD = re.compile(r"\b\d{16,19}\b")
_USCI = re.compile(r"[0-9A-HJ-NP-RTUWXY]{2}\d{6}[0-9A-HJ-NP-RTUWXY]{10}")


def mask_pii(text: str) -> str:
    if not settings.enable_pii_masking:
        return text
    text = _ID_CARD.sub(lambda m: m.group(0)[:6] + "*" * 8 + m.group(0)[-4:], text)
    text = _HK_PHONE.sub(lambda m: m.group(0)[:3] + "****" + m.group(0)[-4:], text)
    text = _PHONE.sub(lambda m: m.group(0)[:3] + "****" + m.group(0)[-4:], text)
    text = _BANK_CARD.sub(lambda m: m.group(0)[:4] + "*" * 8 + m.group(0)[-4:], text)
    text = _USCI.sub(lambda m: m.group(0)[:4] + "*" * 10 + m.group(0)[-4:], text)
    return text


def check_data_residency() -> dict:
    region = settings.data_region
    compliant = region in ("cn", "hk")
    return {
        "data_region": region,
        "compliant": compliant,
        "note": (
            "数据驻留于中国香港/内地，符合 PDPO 与数据本地化要求。"
            if compliant else
            "非中国香港/内地部署不符合数据本地化要求。"
        ),
    }
