# Ceron Frontend

Heron 香港本土化项目的前端（控制台）。对应架构中的 **Next.js + React + TypeScript + MUI** 仪表盘。

- 通过 `/api/*` 反向代理到 **Go 网关**（`backend/go-svc`，默认 `http://localhost:8080`；容器内为 `go-svc:8080`）。
- 当前为最小脚手架：展示网关健康状态并提供文档提交表单，调用 `POST /api/v1/intake` 触发 Go→Python 编排。

## 运行
```bash
npm install
npm run dev          # http://localhost:3000
# 或生产构建：npm run build && npm run start
```
容器化：`API_BASE=http://go-svc:8080 docker compose up --build`（见根目录 docker-compose.yml）。
