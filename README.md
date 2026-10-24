# Ceron — 香港金融业承保与合规自动化平台（Go + Python 混合架构）

Ceron 是面向香港**中小企业金融与保险业**的承保（underwriting）与合规自动化平台。目标客户为香港的**港股保险、信托、家族办公室 / 家族资产**等金融机构。

架构采用**前后端分层、按职责选语言**：
- **后端（Go）**：高并发 IO、收件（API/WhatsApp/企業微信）、异步流水线编排、CRM 同步的「网关/编排层」。
- **后端（Python / FastAPI）**：大模型/ML 密集的「智能服务层」（OCR、抽取、富集、决策）。
- **前端（Next.js）**：面向承保/合规人员的控制台仪表盘。

> 详细产品与技术架构分析见 `产品与技术架构分析.md`。

---

## 产品定位与优势

Ceron 定位为面向香港**中小企业金融与保险业**的**承保（underwriting）与合规自动化平台**——覆盖港股保险承保/理赔、信托、家族办公室 / 家族资产等场景，把「申请/报案 → 抽取 → 核验 → 出核保/理赔结论」全流程自动化，让承保与合规团队在不加人的前提下处理数倍提交量。

### 核心能力流水线（面向香港金融业，做港式改造）
| 阶段 | 说明（Ceron-HK） |
|---|---|
| **Intake 收件** | 多渠道接入：API、客户门户、**WhatsApp Business / 企業微信**（贴合港人使用习惯），自动读取正文与附件 |
| **Classify 分类** | 自动判别文件类型与业务归属（投保单、理赔申请、KYC、月结单、NAR1、信託契約…） |
| **Extract 抽取** | **双语（繁體中文 + 英文，跨境客涉及简体）** 结构化字段抽取，适配 HK 专属文档模板 |
| **Enrich 富集核验** | **ICRIS 公司查冊**、制裁/PEP 名单屏蔽、受益所有权核验、資產來源 CDD |
| **Decisioning 决策** | 风险评分 + **合規閘口（SFC / HKMA / 保監局規則）**，输出 通过 / 拒絕 / 轉人工 并给出理由 |
| **Sync 同步** | 结构化数据直连 Salesforce / Dynamics / 港式核心系统，并保留**完整審計追蹤**（监管刚需） |

### 面向香港的特点与优势
- **「Autopilot, not copilot」**：输出**决策结论**而非仅抽取数据，对比单点 OCR/解析工具，直接缩短承保周期、降低人工差错。
- **双语 + 简繁英三语界面**：前端内置 繁體中文 / English / 简体中文 切换，满足香港金融机构中、英、跨境内地客的多语操作与合规留痕需求。
- **本地合规优先**：内置 PDPO《個人資料（私隱）條例》数据驻留（建议香港区）、PII 脱敏、字段级加密与审计日志；合規閘口对齐 SFC / HKMA / 保監局 与 AML/CFT、KYC/CDD、受益所有權、制裁/PEP 要求。
- **香港专属数据源**：原生对接 ICRIS 查冊、UN/EU/HK MAO 等制裁与 PEP 名单；失败自动降级并打「需人工複核」标记，保证流水线不中断。
- **金融级稳定与扩展**：Go 网关提供高并发、低延迟与强类型编排；异步作业经 Postgres（JSONB）持久化 + NATS JetStream 队列，支持多实例水平扩展与重启不丢。
- **落地快**：采用 Forward-Deployed 式集成，直接接进客户 CRM / 核心系统；提供容器编排（Docker Compose / K8s）与一键本地启动脚本。

### 技术架构优势
- **按职责选语言的混合架构**：Go 负责高性能 IO、编排与集成；Python 负责 LLM/ML 密集的智能服务，各自复用生态、互不拖累。
- **清晰的服务边界**：网关 / 收件 / 编排 / 连接器（Go）与 抽取 / 富集 / 决策（Python FastAPI）职责分明，可独立部署、独立伸缩。
- **前端一致体验**：Next.js + TypeScript + MUI 的承保/合规人员控制台，承载分类结果、抽取字段、核验与决策建议、人工审批看板。

### 业务补充清单（对标香港金融业，待扩展）

当前已覆盖 **港股保险承保/理赔、信托、家族办公室 / 家族资产**。对比香港金融业全貌，建议补充：

| 维度 | 待补充业务线 / 能力 |
|---|---|
| **银行业务（HKMA）** | 开户 KYC/CDD、信贷与**按揭承保**、贸易融资/信用证、虚拟银行 onboarding |
| **证券与经纪（SFC）** | 券商客户 onboarding、IPO 保荐尽调、**合适性评估 (suitability)**、LEI 核验 |
| **强积金 MPF** | 香港专属强积金计划合规核查、雇主/雇员供款主体核验 |
| **基金与资管（SFC Type 9）** | **OFC 开放式基金、LPF 有限合伙基金、REIT** 结构与受益人核验 |
| **私人银行** | 区别于家办的高净值客户尽调、全权委托组合管理合规 |
| **再保险 / 分保** | 分出/分入对手方资信与合约核验 |
| **跨境理财通 (GBA WMC)** | 大湾区跨境财富管理双地身份与额度合规 |
| **合规数据源补强** | 虚拟资产 VATP/稳定币、CRS/FATCA 税务信息交换、土地注册处 Land Search、信贷局（TU HK）、不利媒体筛查、制裁名单补全（OFAC/HMT/FATF 灰名单） |
| **运营流程补强** | 持续尽职（周期性复核 + 触发式 re-KYC）、可疑交易申报 SAR（JFIU）、监管 MI/报送看板、模型治理与可解释性 |

### 落地优先级（按性价比）

- **优先级 1（快赢）**：扩展 `Classify` 业务类型枚举 + `Enrich` 数据源（土地注册、信贷局、OFAC/HMT、CRS）；架构已就绪，主要是加 Provider 与枚举。
- **优先级 2（中，已实现）**：银行业按揭承保（HKMA LTV/DSR 闸口）、证券合适性（风险承受度 vs 产品风险）、MPF（雇主登记/供款合规）、基金/OFC/LPF（证监会认可与零售投资者限制）的合规閘口与决策规则，已落入 `assess()` 与专属抽取 Schema。
- **优先级 3（长线）**：持续监控 + SAR 申报 + 监管 MI 报表（涉及状态机与定时任务）。

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
├── deploy/                   # 部署产物
│   ├── nginx/ceron.conf      # Nginx 反代 + TLS 站点配置
│   └── k8s/                  # K8s 清单（namespace/configmap/secret/3×Deployment+Service/Ingress）
├── docker-compose.yml        # 一键编排 frontend + go-svc + python-svc
├── README.md
└── 产品与技术架构分析.md
```

数据流：`前端 → Go 网关(/v1/intake 或 /v1/ingest/*) → 异步 worker → Python(/v1/pipeline: OCR→抽取→富集→决策) → 决策/路由 → CRM 同步`

---

## 运行方式

> 一键启动（推荐）：仓库内置脚本会自动拉起三个服务并打开前端。
> - Windows：`scripts\start.bat`（停止用 `scripts\stop.bat`，或启动窗口按任意键）
> - Windows(PowerShell)：`scripts\start.ps1`
> - macOS / Linux：`./scripts/start.sh`
> 脚本会自动创建 Python venv 并安装依赖、按需 `npm install`，日志见 `logs/`。

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

**Go 网关**：`GET /health`；`POST /v1/intake`（同步）；`POST /v1/intake/async`（异步，202+轮询）；`POST /v1/ingest/whatsapp`、`POST /v1/ingest/wecom`（渠道收件，默认 insurance_hk）；`GET /v1/jobs?status=&limit=&offset=`（过滤+分页）、`GET /v1/jobs/{id}`；`PATCH /v1/jobs/{id}/review`（人工审批 approved/rejected，含审计：审批人/时间，持久化）；作业完成后自动回调 `CRM_WEBHOOK_URL`（如配置）。

可插拔数据源（`.env` 配置）：LLM（deepseek/qwen/glm/openai/claude）、OCR（azure/tesseract）、Enrichment（ICRIS / 制裁名单），均 mock 兜底，外部源失败自动降级为人工复核标记。

---

## 文档

| 文档 | 内容 |
|---|---|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Windows/macOS/Linux 部署（Docker 与裸机服务化：NSSM/launchd/systemd）、反向代理、验证清单、排障 |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | 运维：拓扑与健康检查、日志、监控、升级回滚、配置变更、**文档同步策略** |

> **文档同步策略**：接口/配置/服务/验证状态发生变化时，必须同步更新 README、`.env.example` 与 docs/（详见 OPERATIONS.md §7）。
