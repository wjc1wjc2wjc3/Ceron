const API_BASE = process.env.API_BASE || "http://localhost:8080";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // 将 /api/* 代理到 Go 网关（开发默认 localhost:8080；容器中为 go-svc:8080）
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_BASE}/:path*` }];
  },
};

export default nextConfig;
