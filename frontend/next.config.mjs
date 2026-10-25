const API_BASE = process.env.API_BASE || "http://localhost:8080";
// 8001 而非 8000：8000 是 AiToken 后端（AiTokenWhole/AiTokenBackend）的端口，
// 两者都绑 8000 时 Windows 上会静默共存（各占 127.0.0.1 / 0.0.0.0），
// 更具体的 127.0.0.1 绑定会把请求抢走，导致 AiToken 前端登录 404 且无任何报错。
const PY_BASE = process.env.PY_BASE || "http://localhost:8001";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // /api/* 代理到 Go 网关；/py/* 代理到 Python 智能服务层（合规运营：监控/SAR/MI）
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_BASE}/:path*` },
      { source: "/py/:path*", destination: `${PY_BASE}/:path*` },
    ];
  },
};

export default nextConfig;
