# Ceron — Heron 的香港金融业本土化（Go + Python 混合架构）

Ceron 是 [Heron Data](https://www.herondata.io/)（面向中小企业金融与保险的承保自动化平台，YC S20，Series A）的**香港版本**。目标客户为香港的**港股保险、信托、家族办公室 / 家族资产**等金融机构。

架构采用**前后端分层、按职责选语言**：
- **后端（Go）**：高并发 IO、收件（API/WhatsApp/企業微信）、异步流水线编排、CRM 同步的「网关/编排层」。
- **后端（Python / FastAPI）**：大模型/ML 密集的「智能服务层」（OCR、抽取、富集、决策）。
- **前端（Next.js）**：面向承保/合规人员的控制台仪表盘。

> 详细产品与技术架构分析见 `Heron产品与技术架构分析.md`。

---

## 目录结构
```
Ceron/
├── frontend/                 # 前端（Next.js + React + TS + MUI）
├── backend/
│   ├── python-svc/           # Python 智能服务层 (FastAPI)
│   │   ├── app/              # config/llm/llm_gateway/regex_extract/schemas/
│   │   │                     #   compliance/ocr/extraction/enrichment/decision/main
│   │   ├── poc/              # 双语抽取准确率 PoC 脚本
│   │   ├── data/samples/     # 繁中/英文/家族办公室样本
│   │   └── tests/            # pytest（脱敏/抽取/OCR/富集/流水线）
│   └── go-svc/               # Go 网关/编排层
│       ├── cmd/server/       # 入口（worker pool + CRM webhook 装配）
│       ├── internal/client/      # 调用 Python 服务的 REST 客户端
│       ├── internal/queue/       # 异步作业 worker pool
│       ├── internal/ingest/      # WhatsApp/企業微信 webhook 收件适配
│       ├── internal/connectors/  # CRM webhook 同步
│       ├── internal/orchestrator/# 同步/异步流水线编排
│       └── internal/handler/     # /v1/intake(+/async)、/v1/ingest/*、/v1/jobs
├── docs/                     # 部署与运维文档（Windows/macOS/Linux）
│   ├── DEPLOYMENT.md
│   └── OPERATIONS.md
├── docker-compose.yml        # 一键编排 frontend + go-svc + python-svc
├── README.md
└── Heron产品与技术架构分析.md
```

数据流：`前端 → Go 网关(/v1/intake 或 /v1/ingest/*) → 异步 worker → Python(/v1/pipeline: OCR→抽取→富集→决策) → 决策/路由 → CRM 同步`

---

## 运行方式

### 后端 Python 智能服务层
```bash
cd backend/python-svc
py -3 -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # 默认全 mock，零密钥可跑
uvicorn app.main:app --port 8000
```

### 后端 Go 网关/编排层
```bash
cd backend/go-svc
# PYTHON_SVC_URL=http://localhost:8000  WORKERS=4
go run ./cmd/server           # 监听 :8080
```

### 前端
```bash
cd frontend && npm install && npm run dev    # http://localhost:3000
```

### Docker 一键编排
```bash
docker compose up --build    # 前端 :3000 → Go :8080 → Python :8000
```

### 双语抽取 PoC
```bash
cd backend/python-svc && py poc/bilingual_poc.py
# 繁中/英文/family_office 三组样本的字段级准确率；配置 LLM_API_KEY 后重跑对比
```

---

## API 概要

**Python 智能服务层**：`GET /health`；`POST /v1/ocr`（image_base64→文本）；`POST /v1/extract`；`POST /v1/enrich`；`POST /v1/decision`；`POST /v1/pipeline`（text 或 image_base64，串联 OCR→抽取→富集→决策）。`vertical` 取值：`insurance_hk`、`family_office`。

**Go 网关**：`GET /health`；`POST /v1/intake`（同步）；`POST /v1/intake/async`（异步，202+轮询）；`POST /v1/ingest/whatsapp`、`POST /v1/ingest/wecom`（渠道收件，默认 insurance_hk）；`GET /v1/jobs/{id}`；作业完成后自动回调 `CRM_WEBHOOK_URL`（如配置）。

可插拔数据源（`.env` 配置）：LLM（deepseek/qwen/glm/openai/claude）、OCR（azure/tesseract）、Enrichment（ICRIS / 制裁名单），均 mock 兜底，外部源失败自动降级为人工复核标记。

---

## 文档

| 文档 | 内容 |
|---|---|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Windows/macOS/Linux 部署（Docker 与裸机服务化：NSSM/launchd/systemd）、反向代理、验证清单、排障 |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | 运维：拓扑与健康检查、日志、监控、升级回滚、配置变更、**文档同步策略** |

> **文档同步策略**：接口/配置/服务/验证状态发生变化时，必须同步更新 README、`.env.example` 与 docs/（详见 OPERATIONS.md §7）。

---

## 已验证
- `pytest`（backend/python-svc）：**9/9 通过**（脱敏、繁中/英正则、OCR mock、富集 Provider、family_office 流水线）。
- 双语 PoC：繁中保险 / 英文保险 / 家族办公室三组样本 **21/21 字段命中（100%）**（mock 正则基线）。
- `go build ./...` 与 `go vet ./...` 全部通过（含 queue/ingest/connectors 新包）。
- 前端：Next.js 控制台已落地（文档提交、抽取/富集/决策结果展示、作业审批看板），`npm install` + `npm run build` 通过。

## 下一步建议
1. 用真实密钥跑双语 PoC，评估国产/国际模型准确率差异（`LLM_API_KEY` 配好后 `py poc/bilingual_poc.py`）；
2. ICRIS / 制裁名单真实凭证接入与联调；
3. Azure OCR 用真实月结单/保单扫描件调优；
4. WhatsApp Cloud API / 企業微信回调真实报文适配（现 ingest 为简化载荷）；
5. 作业表持久化（Postgres）+ NATS/Kafka 替换内存队列。
