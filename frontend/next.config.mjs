const API_BASE = process.env.API_BASE || "http://localhost:8080";
const PY_BASE = process.env.PY_BASE || "http://localhost:8000";

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
