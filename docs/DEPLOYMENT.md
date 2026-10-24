# Ceron 部署文档（Windows / macOS / Linux）

适用组件：`backend/python-svc`（FastAPI 智能服务）、`backend/go-svc`（Go 网关/编排）、`frontend`（Next.js 控制台）。

数据流：`frontend :3000 → go-svc :8080 → python-svc :8000`

---

## 1. 前置依赖

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | 3.12+ | python-svc 运行时 |
| Go | 1.27+ | go-svc 编译 |
| Node.js | 20 LTS | frontend 构建与运行 |
| Docker Desktop / Engine | 24+ | 方式一（推荐） |

## 2. 配置文件

| 文件 | 作用 |
|---|---|
| `backend/python-svc/.env.example` | LLM/OCR/富集数据源/数据驻留/脱敏开关。复制为 `.env` 后修改 |
| `backend/go-svc/.env.example` | `PYTHON_SVC_URL`、`GO_SVC_PORT`、`WORKERS`、`CRM_WEBHOOK_URL` |
| `docker-compose.yml` | 三服务编排（读取各服务环境变量） |

> Go 服务不自动加载 `.env`，启动前请按各 OS 方式设置环境变量（或用 systemd `EnvironmentFile`）。

---

## 3. 方式一：Docker Compose（全平台推荐）

```bash
cd Ceron
docker compose up --build -d
```

- Windows/macOS：安装 Docker Desktop 后直接执行；Linux 安装 Docker Engine。
- 验证：frontend `http://localhost:3000`；go-svc `curl http://localhost:8080/health`；python-svc `curl http://localhost:8000/health`。
- 停止：`docker compose down`；代码更新后：`docker compose up --build -d`。

---

## 4. 方式二：裸机部署 + 服务化

### 4.1 backend/python-svc

```bash
cd backend/python-svc
py -3 -m venv .venv                 # macOS/Linux: python3 -m venv .venv
# Windows: .venv\Scripts\activate   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                # Windows 用 copy
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Windows 服务化（NSSM）**
```powershell
choco install nssm
nssm install CeronPython "C:\...\backend\python-svc\.venv\Scripts\uvicorn.exe" "app.main:app --host 0.0.0.0 --port 8000"
nssm set CeronPython AppDirectory "C:\...\backend\python-svc"
nssm start CeronPython
```
（无 choco 时可用「任务计划程序」开机启动同一命令。）

**macOS 服务化（launchd）** — 存为 `~/Library/LaunchAgents/io.ceron.python.plist`：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>io.ceron.python</string>
  <key>WorkingDirectory</key><string>/path/to/Ceron/backend/python-svc</string>
  <key>ProgramArguments</key><array>
    <string>/path/to/Ceron/backend/python-svc/.venv/bin/uvicorn</string>
    <string>app.main:app</string><string>--host</string><string>0.0.0.0</string>
    <string>--port</string><string>8000</string>
  </array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
</dict></plist>
```
加载：`launchctl load ~/Library/LaunchAgents/io.ceron.python.plist`

**Linux 服务化（systemd）** — 存为 `/etc/systemd/system/ceron-python.service`：
```ini
[Unit]
Description=Ceron Python Intelligence Service
After=network.target

[Service]
WorkingDirectory=/opt/ceron/backend/python-svc
EnvironmentFile=/opt/ceron/backend/python-svc/.env
ExecStart=/opt/ceron/backend/python-svc/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
User=ceron

[Install]
WantedBy=multi-user.target
```
启用：`sudo systemctl enable --now ceron-python`

### 4.2 backend/go-svc

```bash
cd backend/go-svc
go build -o ceron-gateway ./cmd/server     # Windows 产物为 ceron-gateway.exe
# 环境变量（各 OS 均需设置）：
#   PYTHON_SVC_URL=http://localhost:8000  GO_SVC_PORT=8080  WORKERS=4  CRM_WEBHOOK_URL=
./ceron-gateway
```

- **Windows（NSSM）**：`nssm install CeronGateway "C:\...\ceron-gateway.exe"`，并在 `AppEnvironment` 加入上述变量。
- **macOS**：仿 4.1 的 launchd plist，`ProgramArguments` 指向编译产物，`EnvironmentVariables` 注入变量。
- **Linux（systemd）**：`/etc/systemd/system/ceron-gateway.service`，`EnvironmentFile` 指向 env 文件，`After=ceron-python.service`，`Restart=always`。

### 4.3 frontend

```bash
cd frontend
npm install
npm run build
npm run start        # 默认 :3000；跨机部署时设 API_BASE 指向 go-svc
```

- `API_BASE`：开发默认 `http://localhost:8080`；生产跨机时设为 `http://<go-svc-host>:8080`（或走反向代理同域）。
- 服务化：Windows/macOS 参考 4.1/4.2（命令为 `npm run start`）；Linux systemd 同理。
- 说明：本前端含 `/api` 反代 rewrite，需 Node 服务器运行；如需纯静态导出，请改为客户端直连 go-svc 并配置 CORS。

---

## 5. 反向代理与 TLS（生产建议）

用 Nginx/Caddy 统一入口并加 TLS：

```nginx
server {
  listen 443 ssl;
  server_name ceron.example.com;

  location / {
    proxy_pass http://127.0.0.1:3000;   # frontend
    proxy_set_header Host $host;
  }
  location /gateway/ {
    proxy_pass http://127.0.0.1:8080/;  # go-svc
    proxy_set_header Host $host;
  }
}
```

---

## 6. 部署验证清单

1. `curl http://<python-svc>:8000/health` → `{"status":"ok","service":"intelligence",...}`
2. `curl http://<go-svc>:8080/health` → `{"status":"ok","service":"gateway"}`
3. `curl -X POST http://<go-svc>:8080/v1/intake -H "Content-Type: application/json" -d '{"vertical":"insurance_hk","text":"保單號：HK12345\n保額：800萬\n理賠金額：120萬\n資料完整度：0.9"}'` → 返回 job（completed）
4. 打开 frontend，提交表单，能看到处理结果。

---

## 7. 常见部署问题

| 现象 | 原因/处理 |
|---|---|
| go-svc 报连接 python 失败 | `PYTHON_SVC_URL` 未设或 python-svc 未启动 |
| 端口被占用（8000/8080/3000） | 杀掉占用进程或改端口（`GO_SVC_PORT`/compose ports） |
| mock 模式抽取不全 | 正常：正则兜底有限；配置 `LLM_API_KEY` 后由大模型抽取 |
| OCR/富集报「缺少配置」 | 对应 `OCR_PROVIDER`/`ENRICHMENT_PROVIDER` 的 URL/KEY 未配置 |
| Windows 下 go run 提示文件被占用 | 旧进程未退出：结束 `ceron-gateway.exe`/`go.exe` 后重试 |
