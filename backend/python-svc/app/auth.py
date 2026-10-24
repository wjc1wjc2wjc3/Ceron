"""认证与会话：注册/登录、会话令牌、X(Twitter)/Facebook 第三方登录。

设计要点：
- 零第三方依赖：密码用标准库 PBKDF2-HMAC-SHA256（含随机盐 + 迭代），
  会话令牌为 HS256 签名的 JWT（stdlib hmac/hashlib 实现）。
- 用户落库走 ``app.store``：配置 DATABASE_URL 时写 Postgres ``users`` 表，
  否则内存兜底（与 go-svc 一致的降级策略）。
- X 采用 OAuth 2.0 Authorization Code + **PKCE**（S256）；Facebook 采用 OAuth 2.0
  Authorization Code。两者均校验 ``state`` 并设置 10 分钟有效期，防 CSRF/重放。
- 任一社交登录未配置 client_id 时，/v1/auth/providers 返回 false，
  前端据此隐藏/停用对应按钮，避免用户撞到 500。
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
from typing import Optional

import httpx

from app import store
from app.config import settings

PBKDF2_ITER = 120_000

# state -> {verifier, ts}，带 TTL 清理（X / Facebook 共用，state 前缀区分）
_pending: dict[str, dict] = {}
_STATE_TTL = 600


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _clean_pending() -> None:
    now = time.time()
    for k in [k for k, v in _pending.items() if now - v["ts"] > _STATE_TTL]:
        _pending.pop(k, None)


# ============ 密码 ============
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITER)
    return f"pbkdf2_sha256${PBKDF2_ITER}${salt}${_b64e(dk)}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored:
        return False
    try:
        algo, iter_s, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iter_s))
        return hmac.compare_digest(_b64e(dk), digest)
    except Exception:
        return False


# ============ 会话令牌（HS256 JWT，标准库实现）============
def create_token(user: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user["id"],
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "iat": now,
        "exp": now + settings.auth_token_ttl,
    }
    signing = f"{_b64e(json.dumps(header, separators=(',', ':')).encode())}." \
              f"{_b64e(json.dumps(payload, separators=(',', ':')).encode())}"
    sig = hmac.new(settings.auth_secret.encode(), signing.encode(), hashlib.sha256).digest()
    return f"{signing}.{_b64e(sig)}"


def verify_token(token: str) -> Optional[dict]:
    """校验签名与过期时间；返回 payload 或 None。"""
    if not token or token.count(".") != 2:
        return None
    h, p, s = token.split(".")
    expected = _b64e(hmac.new(settings.auth_secret.encode(), f"{h}.{p}".encode(),
                              hashlib.sha256).digest())
    if not hmac.compare_digest(s, expected):
        return None
    try:
        payload = json.loads(_b64d(p))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def public_user(user: dict) -> dict:
    """脱敏后的用户信息（绝不外传 password_hash）。"""
    return {"id": user.get("id"), "email": user.get("email"),
            "name": user.get("name"), "provider": user.get("provider", "email")}


def issue(user: dict) -> dict:
    return {"token": create_token(user), "user": public_user(user)}


# ============ 注册 / 登录 ============
def register(email: str, password: str, name: str = "") -> dict:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("email_invalid")
    if len(password or "") < 8:
        raise ValueError("password_too_short")
    if store.get_user_by_email(email):
        raise ValueError("email_taken")
    user = {
        "id": f"u-{secrets.token_hex(8)}",
        "email": email,
        "password_hash": hash_password(password),
        "name": name or email.split("@")[0],
        "provider": "email",
        "provider_id": None,
        "created_at": store.now_iso(),
    }
    store.create_user(user)
    return user


def login(email: str, password: str) -> Optional[dict]:
    user = store.get_user_by_email((email or "").strip().lower())
    if not user or not verify_password(password, user.get("password_hash")):
        return None
    return user


def upsert_social(provider: str, provider_id: str, email: str, name: str) -> dict:
    """第三方登录：按 provider+provider_id 复用用户，否则按邮箱关联，再否则新建。"""
    user = store.get_user_by_provider(provider, provider_id)
    if user:
        return user
    email = (email or f"{provider_id}@{provider}.local").strip().lower()
    user = store.get_user_by_email(email)
    if user:  # 邮箱已存在：直接复用，避免重复账号
        return user
    user = {
        "id": f"u-{secrets.token_hex(8)}",
        "email": email,
        "password_hash": None,
        "name": name or email.split("@")[0],
        "provider": provider,
        "provider_id": provider_id,
        "created_at": store.now_iso(),
    }
    store.create_user(user)
    return user


# ============ X (Twitter) OAuth 2.0 + PKCE ============
def x_authorize() -> Optional[str]:
    if not settings.x_client_id:
        return None
    _clean_pending()
    verifier = secrets.token_urlsafe(64)
    state = f"x:{secrets.token_urlsafe(16)}"
    _pending[state] = {"verifier": verifier, "ts": time.time()}
    challenge = _b64e(hashlib.sha256(verifier.encode()).digest())
    params = {
        "response_type": "code",
        "client_id": settings.x_client_id,
        "redirect_uri": settings.x_redirect_uri,
        "scope": "tweet.read users.read offline.access",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return "https://twitter.com/i/oauth2/authorize?" + urllib.parse.urlencode(params)


async def x_callback(code: str, state: str) -> dict:
    pending = _pending.pop(state, None)
    if not pending or time.time() - pending["ts"] > _STATE_TTL:
        raise ValueError("invalid_state")
    auth = None
    if settings.x_client_secret:
        auth = (settings.x_client_id, settings.x_client_secret)
    async with httpx.AsyncClient(timeout=15.0) as cli:
        tok = await cli.post(
            "https://api.twitter.com/2/oauth2/token",
            data={"grant_type": "authorization_code", "code": code,
                  "redirect_uri": settings.x_redirect_uri,
                  "client_id": settings.x_client_id,
                  "code_verifier": pending["verifier"]},
            auth=auth,
        )
        tok.raise_for_status()
        access = tok.json().get("access_token")
        if not access:
            raise ValueError("token_exchange_failed")
        me = await cli.get("https://api.twitter.com/2/users/me",
                           headers={"Authorization": f"Bearer {access}"})
        me.raise_for_status()
        data = me.json().get("data", {})
    pid = data.get("id")
    if not pid:
        raise ValueError("profile_missing")
    return upsert_social("x", pid, data.get("email") or "", data.get("name") or data.get("username") or "")


# ============ Facebook OAuth 2.0 ============
def facebook_authorize() -> Optional[str]:
    if not settings.facebook_client_id:
        return None
    _clean_pending()
    state = f"fb:{secrets.token_urlsafe(16)}"
    _pending[state] = {"ts": time.time()}
    params = {
        "client_id": settings.facebook_client_id,
        "redirect_uri": settings.facebook_redirect_uri,
        "scope": "email,public_profile",
        "response_type": "code",
        "state": state,
    }
    return "https://www.facebook.com/v19.0/dialog/oauth?" + urllib.parse.urlencode(params)


async def facebook_callback(code: str, state: str) -> dict:
    pending = _pending.pop(state, None)
    if not pending or time.time() - pending["ts"] > _STATE_TTL:
        raise ValueError("invalid_state")
    async with httpx.AsyncClient(timeout=15.0) as cli:
        tok = await cli.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={"client_id": settings.facebook_client_id,
                    "client_secret": settings.facebook_client_secret,
                    "redirect_uri": settings.facebook_redirect_uri,
                    "code": code},
        )
        tok.raise_for_status()
        access = tok.json().get("access_token")
        if not access:
            raise ValueError("token_exchange_failed")
        me = await cli.get(
            "https://graph.facebook.com/v19.0/me",
            params={"fields": "id,name,email"},
            headers={"Authorization": f"Bearer {access}"},
        )
        me.raise_for_status()
        data = me.json()
    pid = data.get("id")
    if not pid:
        raise ValueError("profile_missing")
    return upsert_social("facebook", pid, data.get("email") or "", data.get("name") or "")


def configured_providers() -> dict:
    return {"email": True, "x": bool(settings.x_client_id),
            "facebook": bool(settings.facebook_client_id)}
