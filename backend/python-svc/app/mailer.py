"""邮件发送器：生产走 SMTP（标准库 smtplib），未配置时回退为「控制台回显」。

本地无 SMTP 也能完整走通验证码 / 重置密码流程：邮件内容会打印到服务日志，
并在响应里回传 `dev_*` 字段（仅当 SMTP 未配置），便于开发调试。
生产环境请务必配置 SMTP_*，响应将不再包含任何令牌/验证码。
"""
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.config import settings


def configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def _print_dev_mail(to: str, subject: str, body: str, secret: str) -> None:
    print(
        f"\n[mailer:dev] SMTP 未配置，邮件未真实发送\n"
        f"  to      : {to}\n"
        f"  subject : {subject}\n"
        f"  body    : {body}\n"
        f"  secret  : {secret}\n",
        flush=True,
    )


def send(to: str, subject: str, body: str, secret: str = "") -> None:
    """发送邮件；未配置 SMTP 时仅回显到日志（不抛异常，保证流程可跑）。"""
    if not configured():
        _print_dev_mail(to, subject, body, secret)
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(body)
    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                if settings.smtp_user:
                    s.login(settings.smtp_user, settings.smtp_pass)
                s.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                s.starttls()
                if settings.smtp_user:
                    s.login(settings.smtp_user, settings.smtp_pass)
                s.send_message(msg)
    except Exception as e:  # 邮件失败不应让认证流程 500
        print(f"[mailer] send failed: {e}", flush=True)


def send_code(email: str, code: str) -> Optional[str]:
    body = (
        f"Your Ceron verification code is: {code}\n\n"
        f"It expires in {settings.auth_code_ttl // 60} minutes. "
        f"If you did not request this, you can ignore this email."
    )
    send(email, "Your Ceron sign-in code", body, secret=code)
    return code if settings.dev_echo_secret and not configured() else None


def send_reset_link(email: str, token: str) -> Optional[str]:
    link = f"{settings.frontend_url.rstrip('/')}/reset?token={token}"
    body = (
        f"We received a request to reset your Ceron password.\n\n"
        f"Reset link (valid {settings.auth_reset_ttl // 60} minutes):\n{link}\n\n"
        f"If you did not request this, you can ignore this email."
    )
    send(email, "Reset your Ceron password", body, secret=link)
    return link if settings.dev_echo_secret and not configured() else None
