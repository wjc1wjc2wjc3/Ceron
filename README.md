# Ceron — 香港金融业承保与合规自动化平台（Go + Python 混合架构）

![Go](https://img.shields.io/badge/Go-1.22-00ADD8?logo=go&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest%2072%20pass-brightgreen)

> **English**: Ceron is an underwriting & compliance automation platform for Hong Kong financial institutions (insurance, trusts, family offices) — multi-channel intake (API / WhatsApp / WeCom), bilingual document extraction, pluggable data enrichment (ICRIS / Land Search / credit bureau / OFAC / HMT / CRS), decisioning with SFC/HKMA/MPFA compliance gates, ongoing monitoring, SAR filing and regulatory MI reporting.

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
- **香港专属数据源**：原生对接 ICRIS 查冊、土地註冊處 Land Search、信貸局（TU HK）、OFAC/HMT 制裁名单与 CRS/FATCA 稅務信息交換；各源可插拔、失败自动降级并打「需人工複核」标记，保证流水线不中断。
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
| **合规数据源补强** | 虚拟资产 VATP/稳定币、CRS/FATCA 税务信息交换（已实现 Provider）、土地注册处 Land Search（已实现 Provider）、信贷局（TU HK，已实现 Provider）、不利媒体筛查、制裁名单补全（OFAC/HMT，已实现 Provider；FATF 灰名单待补） |
| **运营流程补强** | 持续尽职（周期性复核 + 触发式 re-KYC）、可疑交易申报 SAR（JFIU）、监管 MI/报送看板、模型治理与可解释性 |

### 落地优先级（按性价比）

- **优先级 1（快赢，已实现）**：扩展 `Classify` 业务类型枚举 + `Enrich` 数据源 Provider（土地註冊 Land Search、信貸局 TU HK、OFAC/HMT 制裁名单、CRS/FATCA），均已实现为可插拔 Provider，配置对应 `*_API_URL` 即启用、失败自动降级人工复核。
- **优先级 2（中，已实现）**：银行业按揭承保（HKMA LTV/DSR 闸口）、证券合适性（风险承受度 vs 产品风险）、MPF（雇主登记/供款合规）、基金/OFC/LPF（证监会认可与零售投资者限制）的合规閘口与决策规则，已落入 `assess()` 与专属抽取 Schema。
- **优先级 3（长线，已实现）**：持续监控（触发式 re-KYC + 后台周期性重查制裁/OFAC/HMT，命中生成告警）+ SAR 申报（JFIU，草稿→已提交状态机）+ 监管 MI 报表（`/py/v1/mi` 聚合决策/告警/SAR）。前端新增「合规运营」页签整合三者。

---

## 登录注册与控制台鉴权

- **路由**：`/` 为营销落地页（公开），`/products` 为产品与架构（公开），
  **`/app`（承保工作台）与 `/app/compliance`（合规运营）需登录**。
- **注册登录**：三种方式——① 邮箱 + 密码；② **邮箱验证码（免密码）**；③ X / Facebook。
  密码与验证码均以 **PBKDF2-HMAC-SHA256** 哈希存储（随机盐 + 12 万次迭代），会话为
  **HS256 签名令牌**，全部由标准库实现，未引入第三方鉴权依赖。验证码 10 分钟内有效、
  **一次性使用**、重发需等待冷却期（默认 60 秒）；未注册邮箱首次验证码登录即自动开户。
- **忘记密码**：`POST /v1/auth/password/forgot` 发送重置链接（30 分钟有效、**令牌一次性**）；
  未知邮箱同样返回成功以避免账号枚举，且不会真的发信。
- **邮件通道**：配置 `SMTP_*` 即走真实 SMTP（`smtplib`，支持 STARTTLS / SSL）；
  未配置时降级为「控制台回显」，邮件正文打到服务日志并可在响应回显 `dev_code` / `dev_link`
  便于本地联调——**生产请设 `DEV_ECHO_SECRET=false`**，防止令牌经响应泄露。
- **X / Facebook 登录**：配置对应 App 凭证后，`/v1/auth/providers` 返回可用项，
  登录页自动显示「Continue with X / Facebook」按钮（未配置则按钮停用，不会撞到 500）。
  X 走 OAuth 2.0 **PKCE**（S256），两者均校验 `state`（10 分钟有效期）防 CSRF。
- **守卫**：`frontend/src/middleware.ts` 在**服务端**用 Web Crypto 校验令牌签名与
  过期时间——伪造 cookie 也会被拦下重定向到 `/login`。

```dotenv
# python-svc（后端签发令牌）
AUTH_SECRET=change-me-in-production
PUBLIC_BASE_URL=http://localhost:8001
FRONTEND_URL=http://localhost:3000
X_CLIENT_ID=            # developer.x.com 创建 App
X_CLIENT_SECRET=
FACEBOOK_CLIENT_ID=     # developers.facebook.com 创建 App
FACEBOOK_CLIENT_SECRET=

# frontend/.env.local（中间件校验令牌，必须与后端 AUTH_SECRET 一致）
AUTH_SECRET=change-me-in-production
```

> 提示：未拿到 X / Facebook 应用审批前，可先用邮箱注册（`http://localhost:3000/register`）
> 完整体验控制台；社交登录一旦填入凭证即可自动生效。

## 大模型选择（按用户：内置 5 家 + 自定义模型）

平台用户可在控制台 **AI models（`/app/models`）** 自主选择抽取所用的大模型：

- **内置预设**：DeepSeek、Kimi（Moonshot）、GLM（智谱）、Qwen（通义千问）、Doubao（豆包）。
  每家都带默认 `base_url` 与默认模型名，且**均可就地改写**（国产模型迭代快，不写死）。
- **自定义模型**：任意 OpenAI 兼容端点（自建 vLLM / 内部网关 / 新厂商），
  填 **模型名称 + base_url + api_key** 即可接入，并可关闭 `response_format` JSON 模式
  （部分模型不支持该参数；即便开启，遇到 400 也会自动降级重试）。
- **密钥安全**：密钥存服务端，**对外只返回脱敏值**（`sk-ab…9876`）；更新时若回传空值或
  脱敏值，服务端保留原密钥，避免误清空。
- **生效范围**：`/v1/pipeline` 自动使用当前登录用户选定的模型；未登录或未选择时
  回落服务级环境变量（`LLM_PROVIDER=mock` 即零成本运行）。

| 接口 | 说明 |
|---|---|
| `GET /v1/llm/presets` | 内置模型目录（无需登录） |
| `GET/PUT /v1/llm/settings` | 读取 / 保存用户选择（密钥脱敏，需登录） |
| `POST /v1/llm/custom` | 新增自定义模型 |
| `DELETE /v1/llm/custom/{id}` | 删除自定义模型 |
| `POST /v1/llm/test` | 连通性测试：真实发一次极短对话验证模型/地址/密钥 |

## 数据源真实接入示例（ICRIS / 信贷局）

富集层（`backend/python-svc/app/enrichment.py`）对每类数据源实现为可插拔 Provider：
配置对应 `*_API_URL` 即启用**真实外呼**，未配置或调用失败时**自动降级**为
「需人工複核」标记，流水线不中断。ICRIS 与信贷局已实现真实鉴权契约：

### ICRIS（公司註冊處查冊）

支持两种接入形态，在 `.env` 配置：

- **会话态（推荐）**：`ICRIS_AUTH_URL` + `ICRIS_ACCOUNT` 登录换 token，再以
  `Bearer <token>` 查询；兼容 ICRIS e-Services / 持牌数据服务商的 JSON 契约。
- **直连态**：仅 `ICRIS_API_URL` + `ICRIS_API_KEY`，按契约 `POST {company_name}`。

```dotenv
ICRIS_API_URL=https://icris.vendor.example/api/companies
ICRIS_AUTH_URL=https://icris.vendor.example/auth/token
ICRIS_ACCOUNT=your_account
ICRIS_API_KEY=your_key
```

响应归一化为 `icris_verified / icris_company_status / icris_br_status / icris_cr_no`，
并自动识别「已解散 / 已撤銷註冊」标高风险。

### 信贷局（TransUnion HK 等会员机构）

以**会员编号 + API Key**（建议相互 TLS）调用信用报告接口：

```dotenv
CREDIT_BUREAU_API_URL=https://api.tucb.example/v1/credit-reports
CREDIT_BUREAU_API_KEY=your_key
CREDIT_BUREAU_MEMBER_ID=MEM-0001
```

请求头透传 `X-Member-Id` 与 `Authorization: Bearer`，响应归一化为
`credit_score / credit_adverse`。其余数据源（土地註冊 / OFAC / HMT / CRS）配置
`*_API_URL` 即启用，请求/响应契约见各 Provider 文档字符串。

> 注：ICRIS、TU HK 真实接入需持有政府核准凭证或持牌数据服务商账号；代码已接好
> 鉴权、请求契约与失败降级，填入凭证即可外呼真实数据。

## 持久化（Postgres，与 go-svc 对齐）

python-svc 的合规运营状态（决策历史 / 实体 / 监控告警 / SAR）默认存内存；配置
`DATABASE_URL` 后自动切到 Postgres，并复用与 **go-svc 完全一致** 的 `jobs` 表
（JSONB 持久化），另建 `entities / monitoring_alerts / sars` 三张配套表
（DDL 见 `backend/python-svc/app/store.py`）。未配置或连接失败**安全回退内存**——
与 go-svc「`DATABASE_URL` 未设即内存」的行为一致。

```dotenv
DATABASE_URL=postgresql://user:pass@localhost:5432/ceron
```

> 建议与 go-svc 共用同一 Postgres 实例，使 Go 看板与 Python 决策历史落在同一
> `jobs` 表，便于统一查询、审计与水平扩展（多实例 + 重启不丢）。

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
# PYTHON_SVC_URL=http://localhost:8001  WORKERS=4
go run ./cmd/server           # 监听 :8080
```

### 前端
```bash
cd frontend && npm install && npm run dev    # http://localhost:3000
```

### Docker 一键编排
```bash
docker compose up --build    # 前端 :3000 → Go :8080 → Python :8001
```

### CI 与质量门禁

`.github/workflows/ci.yml` 在 push/PR 时自动跑：后端 `pytest` + **抽取准确率回归门禁**
（`poc/benchmark.py --write --fail-under 0.99`，准确率低于阈值即以非 0 退出码失败），
前端 `tsc --noEmit` + `npm run build`。本地可先跑同样的两步自查：

```bash
cd backend/python-svc && pytest -q && py poc/benchmark.py --write --fail-under 0.99
```

### 角色权限（RBAC）

三种角色：**analyst**（发起作业，注册即默认）/ **reviewer**（处置告警、起草与流转 SAR、规则治理）/ **admin**（全部）。

- 注册接口**一律 analyst，不能自提权**；`reviewer`/`admin` 只能由 `ADMIN_EMAILS`（逗号分隔的管理员邮箱清单）授予，或由管理员直接改 `users.role`；
- 受保护写操作：规则休眠/停用、告警处置、SAR 起草与流转（未登录 401、权限不足 403）；规则导出、MI、能力清单等只读能力保持开放；
- 前端按角色自动显隐操作按钮，analyst 看到只读提示。

### 双语抽取 PoC
```bash
cd backend/python-svc && py poc/bilingual_poc.py
# 繁中/英文/family_office 三组样本的字段级准确率；配置 LLM_API_KEY 后重跑对比
```

### 公开评测基准（6 业务线 × 三语）
```bash
cd backend/python-svc && py poc/benchmark.py --write
# 字段级精确匹配；未配置密钥时为「规则兜底基线」（当前 63/63 = 100%），
# 配置 LLM_API_KEY 后重跑即得真实模型准确率；结果写入 docs/eval/benchmark.json
```

## 能力覆盖度与合规治理（P0/P1）

覆盖度数字由 `/v1/capabilities` 实时统计（前端 `/compare` 页直接引用，避免各处手写不一致）：

| 维度 | 覆盖 |
|---|---|
| 业务线（Vertical） | **6**（insurance_hk / trust / family_office / banking_mortgage / securities_suitability / mpf / fund_ofc_lpf 中的全部枚举） |
| 数据源 Provider | **9** 类已实现（ICRIS / 土地註冊處 / 信貸局 / 制裁服務 / OFAC / HMT / CRS / ICIJ Offshore Leaks / OpenSanctions PEP），配置 `*_API_URL` 即启用、失败自动降级；后两类为免费公开库（对标 kyc-analyst 数据源清单） |
| 合规闸口规则 | **21** 条（SFC / HKMA / MPFA / AML-CFT），版本号 `RULE_PACK_VERSION=2026.10.1`，`GET /v1/rules` 可导出 diff 交给合规审阅 |
| 模型预设 | **5** 家 + 自定义 OpenAI-compatible（DeepSeek / Kimi / GLM / Qwen / Doubao） |
| 人工复核检查点 | **10** 个（CP-01…CP-10），四级分级：field（补件）→ source（人工取证）→ gate（合规判断）→ risk（签批） |
| 语言 | 繁中 / English / 简体（界面、抽取、决策理由、审计包全链路） |

治理能力（对标 marble / kyc-analyst 的可审计设计）：

- **作业级 Trace（P1-2）**：`/v1/pipeline` 返回每一步用的模型、数据源、耗时、token 与降级记录（`trace` / `trace_summary`）。
- **审计包导出（P0-4）**：`GET /v1/runs/{run_id}/audit` 一次拿齐 抽取字段 / 脱敏原文预览 / 富集信号 / 规则命中 / 决策理由 / UBO / trace，`schema_version=ceron-audit-1.0`；控制台 Jobs 页一键下载。
- **HITL 分级（P1-4）**：`assess_with_review` 在决策里内嵌 review（gate 级命中可直接拒绝；source 级=数据源降级必须人工取证）。
- **UBO 图穿透（P1-6）**：股权边相乘计算有效持股、识别循环持股；`POST /v1/ubo` / pipeline 内置。
- **MCP 工具层（P1-5）**：`/v1/mcp/tools` + `/v1/mcp`（JSON-RPC 2.0），把 extract / enrich / decide / ubo / rules 暴露给任意 Agent（Dify / n8n / Claude）。
- **可插拔解析器（P1-1）**：PaddleOCR / Docling（MIT）/ Marker / 内置兜底，`GET /v1/parsers` 查看可用性，未安装自动降级、绝不中断流水线。
- **规则休眠/停用（借鉴 marble rule snooze）**：`POST /v1/rules/{rule_id}/state` 免发版即可停用（误报止血）或休眠到指定时刻（数据源维护窗口），执行记录里保留 `skipped`（审计可回答「为什么这条规则没跑」）。
- **抽取 schema 配置化（借鉴 marble 自定义数据模型）**：`data/schema_config.json`（或 `SCHEMA_CONFIG` 指定路径）可覆盖/扩展既有业务线字段（别名同步喂给正则兜底抽取）、或定义全新业务线（如 `crypto_exchange`）——改 JSON 即生效，无需发版；示例见 `data/schema_config.example.json`。

---

## API 概要

**Python 智能服务层**：`GET /health`；`POST /v1/ocr`（image_base64→文本）；`POST /v1/extract`；`POST /v1/enrich`；`POST /v1/decision`；`POST /v1/pipeline`（text 或 image_base64，串联 OCR→抽取→富集→决策，返回 run_id / ubo / trace）；`GET /v1/capabilities`（覆盖度）；`GET /v1/rules`、`GET /v1/rules/version`（规则包导出）；`GET /v1/runs/{id}/audit`（审计包）；`GET /v1/parsers`、`POST /v1/parse`（可插拔解析）；`POST /v1/ubo`（图穿透）；`GET /v1/mcp/tools`、`POST /v1/mcp`（MCP JSON-RPC）。`vertical` 取值：`insurance_hk`、`trust`、`family_office`、`banking_mortgage`、`securities_suitability`、`mpf`、`fund_ofc_lpf`。

**Go 网关**：`GET /health`；`POST /v1/intake`（同步）；`POST /v1/intake/async`（异步，202+轮询）；`POST /v1/ingest/whatsapp`、`POST /v1/ingest/wecom`（渠道收件，默认 insurance_hk）；`GET /v1/jobs?status=&limit=&offset=`（过滤+分页）、`GET /v1/jobs/{id}`；`PATCH /v1/jobs/{id}/review`（人工审批 approved/rejected，含审计：审批人/时间，持久化）；作业完成后自动回调 `CRM_WEBHOOK_URL`（如配置）。

可插拔数据源（`.env` 配置）：LLM（deepseek/qwen/glm/openai/claude）、OCR（azure/tesseract）、Enrichment（ICRIS / 制裁名单），均 mock 兜底，外部源失败自动降级为人工复核标记。

---

## 文档

| 文档 | 内容 |
|---|---|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Windows/macOS/Linux 部署（Docker 与裸机服务化：NSSM/launchd/systemd）、反向代理、验证清单、排障 |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | 运维：拓扑与健康检查、日志、监控、升级回滚、配置变更、**文档同步策略** |

> **文档同步策略**：接口/配置/服务/验证状态发生变化时，必须同步更新 README、`.env.example` 与 docs/（详见 OPERATIONS.md §7）。
