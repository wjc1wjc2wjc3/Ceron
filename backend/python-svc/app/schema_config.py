"""抽取 schema 配置化（借鉴 marble 的自定义数据模型）。

marble 允许风险团队用「自定义数据模型」镜像自己的数据仓库；Ceron 对应的做法是
把抽取 schema 从硬编码 pydantic 类改为**可用 JSON 配置覆盖/扩展**：

- 配置文件：``data/schema_config.json``（或 ``SCHEMA_CONFIG`` 环境变量指定路径）；
- 能力一：覆盖既有业务线字段（改名/改类型/加别名——别名会同时喂给正则兜底抽取）；
- 能力二：定义全新业务线（如 ``crypto_exchange``），流水线自动用通用兜底规则，
  不需要改 Python 代码、不需要发版；
- 配置文件缺失/损坏时自动回退内置 schema，**绝不中断流水线**；
- 文件修改后自动热加载（按 mtime），运维改 JSON 即生效。

JSON 格式::

    {
      "family_office": {
        "fields": [
          {"name": "资产规模港币万", "type": "float", "aliases": ["AUM", "资产规模"]},
          {"name": "信托设立地", "type": "str"}
        ]
      },
      "crypto_exchange": {
        "fields": [{"name": "客户姓名或实体名称", "type": "str"}, ...]
      }
    }
"""
import json
import os
import threading
from typing import Optional

from app.config import settings

# 运行期缓存：按配置文件 mtime 失效（热加载）
_cache: dict = {"mtime": None, "spec": {}}
_lock = threading.Lock()

_TYPE_MAP = {"str": str, "float": float, "bool": bool}
_ALIASES_KEY = "aliases"


def config_path() -> str:
    return settings.schema_config or os.path.join("data", "schema_config.json")


def _load() -> dict:
    """读取配置（带 mtime 缓存）；缺失/损坏一律返回空 dict。"""
    path = config_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    with _lock:
        if _cache["mtime"] == mtime:
            return _cache["spec"]
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {}  # 配置损坏：忽略配置，回退内置 schema
        spec = data if isinstance(data, dict) else {}
        _cache["mtime"] = mtime
        _cache["spec"] = spec
    return spec


def spec_for(vertical_key: str) -> Optional[dict]:
    """某业务线的配置 spec（无配置返回 None）。"""
    vkey = str(vertical_key)
    spec = _load().get(vkey)
    if isinstance(spec, dict) and isinstance(spec.get("fields"), list) and spec["fields"]:
        return spec
    return None


def is_configured() -> bool:
    return bool(_load())


def _builtin_spec(builtin_model) -> dict:
    """把内置 pydantic schema 反射成统一 FieldSpec（供合并）。"""
    out: dict = {}
    try:
        for name, fi in builtin_model.model_fields.items():
            ann = fi.annotation
            origin = getattr(ann, "__origin__", None)
            base = ann.__args__[0] if origin is not None and getattr(ann, "__args__", None) else ann
            if base is float:
                ftype = "float"
            elif base is bool:
                ftype = "bool"
            else:
                ftype = "str"
            out[name] = {"name": name, "type": ftype, _ALIASES_KEY: []}
    except Exception:
        pass
    return out


def fields_for(vertical_key: str, builtin_model=None) -> list[dict]:
    """合并后的字段清单：内置字段 + 配置覆盖（同名改类型/别名）+ 配置新增。"""
    vkey = str(vertical_key)
    merged = _builtin_spec(builtin_model) if builtin_model is not None else {}
    spec = spec_for(vkey)
    if spec:
        for f in spec["fields"]:
            if not isinstance(f, dict) or not f.get("name"):
                continue
            name = str(f["name"]).strip()
            entry = merged.get(name) or {"name": name, "type": "str", _ALIASES_KEY: []}
            if f.get("type") in _TYPE_MAP:
                entry["type"] = f["type"]
            aliases = f.get(_ALIASES_KEY)
            if isinstance(aliases, list):
                entry[_ALIASES_KEY] = [str(a) for a in aliases if a]
            merged[name] = entry
    return list(merged.values())


def build_model(vertical_key: str, builtin_model=None):
    """按合并后的字段动态构建 pydantic 模型；无配置时返回 None（走内置）。"""
    if not spec_for(vertical_key):
        return None
    try:
        from pydantic import create_model

        fields = {}
        for f in fields_for(vertical_key, builtin_model):
            pytype = _TYPE_MAP.get(f["type"], str)
            fields[f["name"]] = (Optional[pytype], None)  # 全部可选：缺失不阻断流水线
        return create_model(f"CeronDynamic_{str(vertical_key).title().replace('_', '')}", **fields)
    except Exception:
        return None  # 动态建模失败：回退内置 schema


def extra_labels() -> list[tuple[str, str]]:
    """配置中的别名 → 字段名映射（喂给正则兜底抽取，让配置化字段在无 LLM 时也能命中）。"""
    labels: list[tuple[str, str]] = []
    for vkey, spec in _load().items():
        if not isinstance(spec, dict):
            continue
        for f in spec.get("fields") or []:
            if not isinstance(f, dict) or not f.get("name"):
                continue
            name = str(f["name"]).strip()
            labels.append((name, name))
            for a in f.get(_ALIASES_KEY) or []:
                labels.append((str(a), name))
    return labels


def known_verticals(builtin: list[str]) -> list[str]:
    """内置业务线 + 配置新增业务线（配置可扩展全新 vertical）。"""
    extra = sorted(k for k in _load() if k not in set(builtin))
    return list(builtin) + extra
