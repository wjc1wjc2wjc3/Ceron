# Ceron Frontend

Ceron 项目的前端控制台，采用 **Next.js 14 (App Router) + React + TypeScript + MUI**。

通过 `/api/*` 反向代理到 **Go 网关**（`backend/go-svc`，默认 `http://localhost:8080`；容器内为 `go-svc:8080`）。

## 功能
- **文档提交**：选择垂直场景（港股保险 / 家族办公室 KYC），粘贴文本或一键载入示例；支持同步提交与「异步提交（看板轮询）」。
- **结果展示**：抽取字段表、富集结果（数据源 / ICRIS 核验 / 制裁命中 / 风险 / 复核标记）、决策建议（通过/人工复核/驳回 + 理由）。
- **作业审批看板**：作业卡片展示状态与决策；支持人工「通过 / 驳回」复核标记；异步作业自动轮询 `/v1/jobs/{id}` 直至完成。

## 运行
```bash
npm install
npm run dev          # http://localhost:3000（开发）
# 或生产构建：npm run build && npm run start
```
容器化：在根目录 `docker compose up --build`（frontend 服务已编排，内部 `API_BASE=http://go-svc:8080`）。

## 依赖
`next` 14.2.5、`react` 18.3.1、`@mui/material` + `@mui/icons-material` 5.16.7。
