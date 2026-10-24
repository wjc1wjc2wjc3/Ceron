# Heron 产品与技术架构分析（用于香港金融业本土化 → Ceron）

> 分析对象：Heron Data（https://www.herondata.io/）
> 本土化目标市场：香港金融业 —— 港股、保险、信托、家族办公室 / 家族资产
> 用途：供决策参考，确定 Ceron 的产品边界与技术选型，再启动下一步落地。

---

## 1. 公司背景
- 成立：2020 年，YC S20（美国），总部纽约，团队约 60 人，伦敦亦有工程岗。
- 融资：Series A，累计约 **$16.73M**（最近一轮约 $16.6M）。
- 定位：**面向中小企业金融与保险业的承保（underwriting）自动化平台**。
- 合规：SOC 2，API 可用性 99.99%。

## 2. 产品分析
### 2.1 解决的核心问题
小企业申请贷款/保险时，材料（申请表、银行流水、ISO 报表、税务文件）高度非结构化、人工处理慢且易错。Heron 把「申请 → 出额度/出核保结论」全流程自动化，让承保团队在不加人的情况下处理 2 倍提交量。

### 2.2 目标客户与场景（美国）
- 200+ funders / brokers / fintechs。
- 场景：MCA（商户现金垫款）、term loan、SBA、商业保险、信用额度、收入基金融资。
- 吞吐：每日分析 60,000+ 家小企业。

### 2.3 能力模块（产品流水线）
| 阶段 | 说明 |
|---|---|
| **Receive / Intake** | 自动读取邮件正文与所有附件；也支持 API 接入 |
| **Classify** | 自动分类文件类型与业务归属 |
| **Parse / Extract** | 银行流水、ISO 报表「scrubbing」，抽取结构化字段 |
| **Enrich** | 现金流分析、欺诈检测、背景调查、工商核查 |
| **Decisioning** | 按客户自定义信用政策跑检查，输出通过/拒绝/转人工，并说明理由 |
| **Sync** | 结构化数据直接同步到 CRM / 核心系统 |

### 2.4 关键差异化
- 口号 "Autopilot, not copilot"：输出**决策**而非仅抽取数据（对比 Ocrolus 止步于报表解析）。
- 由 **Forward Deployed Engineer** 把 Heron 直接接进客户 CRM，落地快于自研。

## 3. 前端技术架构（来自官方招聘信息）
- **Next.js**（React）+ **TypeScript** + **MUI**（Material UI）。
- 部署：**Vercel**。
- 形态：面向承保人员/分析师的**客户仪表盘（dashboard）**。
- （推断）通过 REST / WebSocket 与后端通信，承载分类结果、抽取字段、决策建议与人工复核界面。

## 4. 后端技术架构
- **语言/框架**：Python，主要使用 **Flask / FastAPI**（微服务化）。
- **智能层**：**LLM + ML**（文档抽取、决策），**Data Engineering / Data Modeling**（特征与数据管道）。
- **异步处理**：文档接入 → 分类 → 抽取 → 富集 → 决策 的流水线，需任务队列/异步 worker。
- **存储（推断）**：关系库（Postgres）+ 对象存储（S3/GCS）+ 检索/向量能力。
- **集成层**：REST API + CRM 原生连接器 + webhooks，由 FDE 落地。

## 5. 基础设施与合规
- **云**：GCP / AWS；**IaC**：Terraform；**CI/CD** 完备。
- **合规**：SOC 2；高可用（99.99% uptime）。

---

## 6. 香港本土化差异与改造建议（Ceron for HK）

### 6.1 市场 / 合规差异
| 维度 | Heron（美国） | Ceron（香港金融业） |
|---|---|---|
| 监管 | 美国各州信贷/保险法规 | **SFC / HKMA / 保险业监管局**，AML/CFT，KYC/CDD，受益所有权，制裁/PEP 名单 |
| 隐私 | 美国金融隐私法 | **PDPO《個人資料（私隱）條例》**；建议数据驻留香港区 |
| 文档 | 美国银行流水、ISO 报表、税表 | **NAR1、ICRIS 公司查冊、審計財報、信託契約、KYC 文件、資產來源證明、港股持倉/券商月結單** |
| 语言 | 英文 | **英文 + 繁體中文**（跨境内地客涉及简体），需双语 OCR/抽取 |
| 客户交互 | 邮件 + CRM | 增加 **WhatsApp Business / 客戶門戶** 适配港人使用习惯 |

### 6.2 产品模块映射（Heron → Ceron-HK）
- **Intake**：邮件 / API / 客户门户 / **WhatsApp Business** 多入口。
- **Classify / Parse**：双语（繁中+英）抽取，HK 专属文档模板（信托契約、NAR1、月结单等）。
- **Enrich**：**ICRIS 查冊**、制裁/PEP 屏蔽、受益所有权图谱、资产来源核验。
- **Decisioning**：风险评分 + **合規閘口（SFC/HKMA 规则）**，路由至 RM / 受托人 / 合规。
- **Sync**：Salesforce / Dynamics / 核心系统 + **完整审计追踪**（监管刚需）。

### 6.3 技术架构建议（Ceron-HK，Go + Python 混合）
采用**前后端分层、按职责选语言**的混合架构：Go 负责高性能 IO、编排与集成；Python 负责大模型/ML 密集的智能服务。

**Go 侧（核心后端 / 基础设施）**
- 技术：Gin / Echo + gRPC（内部服务间）；事件总线 **NATS / Kafka**；Postgres + Redis。
- 服务边界：
  - `gateway`：统一 API 网关、鉴权、审计日志、合规中间件（PDPO 数据驻留、字段级加密）。
  - `ingestion`：多入口收件（邮件 / API / 客户门户 / **WhatsApp Business**）。
  - `orchestrator`：文档处理**状态机/流水线编排**（接收→分类→抽取→富集→决策→路由）。
  - `connectors`：CRM / 核心系统同步（Salesforce、Dynamics、港式核心系统）、webhooks。
- 优势：高并发、低延迟、强类型、易运维，适合金融级稳定与吞吐。

**Python 侧（LLM / ML 智能服务，FastAPI 微服务）**
- 技术：FastAPI + pydantic；LLM SDK（OpenAI 兼容）、OCR 库、pandas 等。
- 服务边界：
  - `extraction`：文档抽取（双语 繁中+英），字段结构化（对接 LLM）。
  - `enrichment`：ICRIS 查冊、制裁/PEP 屏蔽、受益所有權圖譜、資產來源核驗。
  - `decision`：风险评分 + 合規閘口（SFC/HKMA 规则）+ 路由建议。
  - `llm-gateway`（可选）：统一封装模型调用、prompt 管理、fallback 与成本/限流。
- 优势：直接复用 Python 的 LLM/ML 生态，避免重造轮子；与上一版 `Ceron/` 原型（FastAPI 抽取+合规+决策）无缝衔接。

**服务间协作**
- 异步文档流水线：Go `ingestion` 收件 → 发布任务到 NATS/Kafka → Python worker 消费并完成抽取/富集/决策 → 回写结果 → Go `orchestrator` 持久化、合规校验并路由/同步。
- 同步调用（如实时决策）走内部 gRPC/REST。

**其他**
- **前端**：Next.js + React + TS + MUI + **i18n(zh-HK / en)**，部署 Vercel 或香港节点。
- **LLM**：繁中能力强的模型（Claude / GPT-4o via Azure）；家族资产等敏感数据建议**私有化/本地模型**。
- **OCR**：Azure Form Recognizer 或繁中专用 OCR。
- **数据**：Postgres + 对象存储（**AWS ap-east-1 香港 / GCP 香港**）+ 向量库。
- **合规**：PDPO 数据驻留、加密、审计日志、角色权限。

> 注：上一版 `Ceron/` 原型（app/ 下 FastAPI 抽取+合规+决策）即对应本架构的 **Python 智能服务层**，可直接演进为 `extraction / decision` 服务，无需推倒重来；Go 侧为新增基础设施层。

## 7. 下一步可选方向（待确认）
- **A. 保险承保/理赔文档自动化 MVP**（抽取+分类+合规校验）—— 最快验证、监管价值高。
- **B. 家族办公室 KYC / 资产来源 CDD 自动化**（双语抽取 + ICRIS + 受益所有权图谱）—— 客单价高、差异化强。
- **C. 完整平台**（抽取 + enrich + decision + CRM 同步）—— 周期长、投入大。
- **技术验证优先项**：双语 OCR/抽取准确率 PoC（繁中 + 英文港式文档）。

---
*附：上一版 `Ceron/` 原型为「内地商业贷款」场景，技术骨架（FastAPI 抽取流水线、PII 脱敏、决策引擎）与 HK 版高度可复用，建议作为底座而非推倒重来。*
