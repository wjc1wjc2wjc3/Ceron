import { NextRequest, NextResponse } from "next/server";

/**
 * 控制台路由守卫：未登录访问 /app/* 一律重定向到 /login。
 *
 * 这里在服务端用 Web Crypto 校验 HS256 会话令牌的签名与过期时间，
 * 因此仅把 cookie 塞成任意值是进不去控制台的（密钥须与 python-svc AUTH_SECRET 一致）。
 */
const DEV_SECRET = "ceron-dev-secret-change-me";

function b64urlToBytes(s: string): Uint8Array {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/") + pad;
  const bin = atob(b64);
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

async function isValid(token: string, secret: string): Promise<boolean> {
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  const [h, p, s] = parts;
  try {
    const key = await crypto.subtle.importKey(
      "raw", new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" }, false, ["verify"]
    );
    const ok = await crypto.subtle.verify(
      "HMAC", key, b64urlToBytes(s), new TextEncoder().encode(`${h}.${p}`)
    );
    if (!ok) return false;
    const payload = JSON.parse(new TextDecoder().decode(b64urlToBytes(p)));
    return Number(payload.exp) > Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

export async function middleware(req: NextRequest) {
  const token = req.cookies.get("ceron_token")?.value;
  const secret = process.env.AUTH_SECRET || DEV_SECRET;
  if (token && (await isValid(token, secret))) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = "";
  url.searchParams.set("next", req.nextUrl.pathname);
  return NextResponse.redirect(url);
}

export const config = { matcher: ["/app/:path*"] };
