"""合规运营状态存储（决策历史 / 实体 / 监控告警 / SAR）。

默认内存版（零外部依赖，POC 可直接跑）；配置 ``DATABASE_URL`` 后自动切到
Postgres，并复用与 **go-svc 完全一致** 的 ``jobs`` 表（JSONB 持久化），另建
``entities`` / ``monitoring_alerts`` / ``sars`` 三张配套表（见 ``_PG_DDL``）。
未配置或连接失败时安全回退内存，保证流水线不中断——与 go-svc
「``DATABASE_URL`` 未设即内存」的行为一致。

为兼容既有测试，模块级列表 ``pipeline_runs / entities / alerts / sars`` 始终保留；
仅当 ``DATABASE_URL`` 配置且连接成功时，公共 API 才改走 Postgres 后端。
"""
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import settings

_lock = threading.Lock()
pipeline_runs: list[dict] = []
entities: list[dict] = []
alerts: list[dict] = []
sars: list[dict] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(dt: Any) -> str:
    if dt is None:
        return now_iso()
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


# ============ Postgres 后端（与 go-svc jobs 表对齐）============
_PG_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
  id            TEXT PRIMARY KEY,
  vertical      TEXT NOT NULL DEFAULT '',
  status        TEXT NOT NULL DEFAULT 'queued',
  result        JSONB,
  error         TEXT,
  review_status TEXT NOT NULL DEFAULT '',
  review_note   TEXT,
  reviewed_by   TEXT NOT NULL DEFAULT '',
  reviewed_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS entities (
  name       TEXT PRIMARY KEY,
  vertical   TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS monitoring_alerts (
  id     SERIAL PRIMARY KEY,
  ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
  name   TEXT NOT NULL DEFAULT '',
  reason TEXT NOT NULL DEFAULT '',
  lists  JSONB,
  status TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE IF NOT EXISTS sars (
  id      TEXT PRIMARY KEY,
  ts      TIMESTAMPTZ NOT NULL DEFAULT now(),
  status  TEXT NOT NULL DEFAULT 'draft',
  payload JSONB
);
CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  name          TEXT NOT NULL DEFAULT '',
  provider      TEXT NOT NULL DEFAULT 'email',
  provider_id   TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS users_provider_uidx
  ON users(provider, provider_id) WHERE provider_id IS NOT NULL;
"""


class PostgresBackend:
    """基于 psycopg2 连接池的持久化后端（仅在与 go-svc 一致的 schema 上工作）。"""

    def __init__(self, dsn: str) -> None:
        import psycopg2
        from psycopg2 import pool  # 延迟导入：无 DATABASE_URL 时不引入该依赖

        self._pool = pool.ThreadedConnectionPool(1, 5, dsn)
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(_PG_DDL)

    @contextmanager
    def _conn(self):
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    # --- 决策历史 / 实体 ---
    def record_run(self, vertical, action, risk_score, name, job_id):
        from psycopg2.extras import Json

        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO jobs (id, vertical, status, result, created_at)
                VALUES (%s, %s, 'decided', %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    vertical = EXCLUDED.vertical,
                    status   = 'decided',
                    result   = EXCLUDED.result
                """,
                (job_id, vertical, Json({"action": action, "risk_score": risk_score, "name": name})),
            )
            if name:
                cur.execute(
                    "INSERT INTO entities (name, vertical) VALUES (%s, %s) "
                    "ON CONFLICT (name) DO NOTHING",
                    (name, vertical),
                )

    def list_runs(self):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT vertical, result, created_at FROM jobs ORDER BY created_at DESC")
            rows = cur.fetchall()
        out = []
        for vertical, result, created_at in rows:
            result = result or {}
            out.append({
                "ts": _iso(created_at),
                "vertical": vertical,
                "action": result.get("action", "decided"),
                "risk_score": int(result.get("risk_score", 0) or 0),
                "name": result.get("name"),
            })
        return out

    def list_entities(self):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name, vertical, created_at FROM entities ORDER BY created_at DESC")
            rows = cur.fetchall()
        return [{"name": n, "vertical": v, "ts": _iso(t)} for n, v, t in rows]

    # --- 监控告警 ---
    def add_alert(self, name, reason, lists):
        from psycopg2.extras import Json

        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO monitoring_alerts (name, reason, lists, status) "
                "VALUES (%s, %s, %s, 'open') RETURNING id, ts",
                (name, reason, Json(lists or [])),
            )
            row = cur.fetchone()
        return {"id": row[0], "ts": _iso(row[1]), "name": name,
                "reason": reason, "lists": lists or [], "status": "open"}

    def list_alerts(self):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, ts, name, reason, lists, status "
                        "FROM monitoring_alerts ORDER BY ts DESC")
            rows = cur.fetchall()
        return [
            {"id": r[0], "ts": _iso(r[1]), "name": r[2], "reason": r[3],
             "lists": r[4] or [], "status": r[5]}
            for r in rows
        ]

    # --- SAR ---
    def add_sar(self, payload):
        from psycopg2.extras import Json

        sar_id = payload.get("id") or f"SAR-{uuid.uuid4().hex[:6].upper()}"
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sars (id, status, payload) VALUES (%s, 'draft', %s) "
                "ON CONFLICT (id) DO NOTHING RETURNING ts",
                (sar_id, Json(payload)),
            )
            row = cur.fetchone()
        return {"id": sar_id, "ts": _iso(row[0]) if row else now_iso(),
                "status": "draft", **payload}

    def list_sars(self):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, ts, status, payload FROM sars ORDER BY ts DESC")
            rows = cur.fetchall()
        return [{"id": r[0], "ts": _iso(r[1]), "status": r[2], **(r[3] or {})} for r in rows]

    def update_sar(self, sar_id, status):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE sars SET status=%s WHERE id=%s", (status, sar_id))
            if cur.rowcount == 0:
                return None
            cur.execute("SELECT id, ts, status, payload FROM sars WHERE id=%s", (sar_id,))
            r = cur.fetchone()
        return {"id": r[0], "ts": _iso(r[1]), "status": r[2], **(r[3] or {})}


    # --- 用户 ---
    def create_user(self, user: dict) -> dict:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (id, email, password_hash, name, provider, provider_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (user["id"], user["email"], user.get("password_hash"), user.get("name", ""),
                 user.get("provider", "email"), user.get("provider_id")),
            )
        return user

    def get_user_by_email(self, email: str):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, email, password_hash, name, provider, provider_id, created_at "
                        "FROM users WHERE email = %s", (email,))
            r = cur.fetchone()
        return self._row_to_user(r) if r else None

    def get_user_by_provider(self, provider: str, provider_id: str):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, email, password_hash, name, provider, provider_id, created_at "
                        "FROM users WHERE provider = %s AND provider_id = %s", (provider, provider_id))
            r = cur.fetchone()
        return self._row_to_user(r) if r else None

    def get_user_by_id(self, user_id: str):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, email, password_hash, name, provider, provider_id, created_at "
                        "FROM users WHERE id = %s", (user_id,))
            r = cur.fetchone()
        return self._row_to_user(r) if r else None

    @staticmethod
    def _row_to_user(r) -> dict:
        return {"id": r[0], "email": r[1], "password_hash": r[2], "name": r[3],
                "provider": r[4], "provider_id": r[5], "created_at": _iso(r[6])}


def _create_backend() -> Optional[PostgresBackend]:
    url = getattr(settings, "database_url", "") or os.getenv("DATABASE_URL", "")
    if not url:
        return None
    try:
        return PostgresBackend(url)
    except Exception as e:  # 连接失败安全回退内存
        print(f"[store] Postgres 连接失败，回退内存存储：{e}")
        return None


_pg = _create_backend()


# ============ 公共 API（内存 / Postgres 统一入口）============
def record_run(vertical: str, action: str, risk_score: int,
               name: Optional[str] = None, job_id: Optional[str] = None) -> None:
    """记录一次决策结果，并登记实体供持续监控。"""
    if _pg is not None:
        _pg.record_run(vertical, action, risk_score, name,
                       job_id or f"PY-{uuid.uuid4().hex[:12]}")
        return
    with _lock:
        pipeline_runs.append({
            "ts": now_iso(),
            "vertical": vertical,
            "action": action,
            "risk_score": risk_score,
            "name": name,
        })
        if name:
            if not any(e["name"] == name for e in entities):
                entities.append({"name": name, "vertical": vertical, "ts": now_iso()})


def list_runs() -> list[dict]:
    if _pg is not None:
        return _pg.list_runs()
    with _lock:
        return list(pipeline_runs)


def list_entities() -> list[dict]:
    if _pg is not None:
        return _pg.list_entities()
    with _lock:
        return list(entities)


def add_alert(name: str, reason: str, lists: Optional[list] = None) -> dict:
    if _pg is not None:
        return _pg.add_alert(name, reason, lists)
    with _lock:
        a = {
            "id": len(alerts) + 1,
            "ts": now_iso(),
            "name": name,
            "reason": reason,
            "lists": lists or [],
            "status": "open",
        }
        alerts.append(a)
        return a


def list_alerts() -> list[dict]:
    if _pg is not None:
        return _pg.list_alerts()
    with _lock:
        return list(alerts)


def add_sar(payload: dict) -> dict:
    if _pg is not None:
        return _pg.add_sar(payload)
    with _lock:
        sar_id = payload.get("id") or f"SAR-{len(sars) + 1:04d}"
        s = {"id": sar_id, "ts": now_iso(), "status": "draft", **payload}
        sars.append(s)
        return s


def list_sars() -> list[dict]:
    if _pg is not None:
        return _pg.list_sars()
    with _lock:
        return list(sars)


def update_sar(sar_id: str, status: str) -> Optional[dict]:
    if _pg is not None:
        return _pg.update_sar(sar_id, status)
    with _lock:
        for s in sars:
            if s["id"] == sar_id:
                s["status"] = status
                return s
        return None


def _count(items: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for it in items:
        k = it.get(key, "unknown")
        out[k] = out.get(k, 0) + 1
    return out


# ============ 用户（邮箱/密码 或 X / Facebook 第三方登录）============
_users: dict[str, dict] = {}


def create_user(user: dict) -> dict:
    if _pg is not None:
        return _pg.create_user(user)
    with _lock:
        _users[user["id"]] = user
        return user


def get_user_by_email(email: str) -> Optional[dict]:
    if _pg is not None:
        return _pg.get_user_by_email(email)
    with _lock:
        return next((u for u in _users.values() if u["email"] == email), None)


def get_user_by_provider(provider: str, provider_id: str) -> Optional[dict]:
    if _pg is not None:
        return _pg.get_user_by_provider(provider, provider_id)
    with _lock:
        return next((u for u in _users.values()
                     if u.get("provider") == provider and u.get("provider_id") == provider_id), None)


def get_user_by_id(user_id: str) -> Optional[dict]:
    if _pg is not None:
        return _pg.get_user_by_id(user_id)
    with _lock:
        return _users.get(user_id)
