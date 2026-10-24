# Ceron 部署文档（Windows / macOS / Linux）

适用组件：`backend/python-svc`（FastAPI 智能服务）、`backend/go-svc`（Go 网关/编排）、`frontend`（Next.js 控制台）。

数据流：`frontend :3000 → go-svc :8080 → python-svc :8000`

部署产物目录 `deploy/`：
- `deploy/nginx/ceron.conf` — Nginx 反代 + TLS 站点配置
- `deploy/k8s/` — Kubernetes 清单（namespace / configmap / secret / 三个 Deployment+Service / Ingress / kustomization）

---

## 1. 前置依赖

| 组件 | 版本 | 适用方式 |
|---|---|---|
| Python | 3.12+ | 裸机 python-svc |
| Go | 1.27+ | 裸机 go-svc 编译 |
| Node.js | 20 LTS | 裸机 frontend |
| Docker Desktop / Engine | 24+ | Docker / Compose 方式 |
| kubectl | 1.29+ | Kubernetes 方式 |
| Nginx | 1.24+ | Nginx 反代方式 |

## 2. 配置文件

| 文件 | 作用 |
|---|---|
| `backend/python-svc/.env.example` | LLM/OCR/富集/数据驻留/脱敏开关。复制为 `.env` 后修改 |
| `backend/go-svc/.env.example` | `PYTHON_SVC_URL`、`GO_SVC_PORT`、`WORKERS`、`CRM_WEBHOOK_URL` |
| `docker-compose.yml` | 三服务本地编排（读取各服务环境变量） |
| `deploy/k8s/01-configmap.yaml` / `02-secret.yaml` | K8s 非密/敏感配置（含 `LLM_API_KEY` 等） |

> Go 服务不自动加载 `.env`，裸机请用 systemd `EnvironmentFile` 或 NSSM `AppEnvironment` 注入；容器内/K8s 通过环境变量或 ConfigMap/Secret 注入。

镜像约定（K8s / 私有仓库用）：`ceron/python-svc:latest`、`ceron/go-svc:latest`、`ceron/frontend:latest`。

---

## 3. 方式一：Docker / Docker Compose（全平台推荐）

### 3.1 本地一键编排
```bash
cd Ceron
docker compose up --build -d
```
- Windows/macOS：安装 Docker Desktop 后直接执行；Linux 安装 Docker Engine。
- 验证：frontend `http://localhost:3000`；go-svc `curl http://localhost:8080/health`；python-svc `curl http://localhost:8000/health`。
- 停止：`docker compose down`；更新：`docker compose up --build -d`。

### 3.2 单容器手动运行（便于排错 / 指定 registry）
```bash
# python-svc
docker run -d --name python-svc -p 8000:8000 \
  -e LLM_PROVIDER=mock -e DATA_REGION=hk ceron/python-svc:latest

# go-svc（需能访问 python-svc 地址；同主机用宿主 IP 或 --network）
docker run -d --name go-svc -p 8080:8080 \
  -e PYTHON_SVC_URL=http://<python-host>:8000 -e GO_SVC_PORT=8080 \
  -e WORKERS=4 ceron/go-svc:latest

# frontend
docker run -d --name frontend -p 3000:3000 \
  -e API_BASE=http://<go-host>:8080 ceron/frontend:latest
```

### 3.3 构建并推送到镜像仓库（供 K8s / 远程主机）
跨平台构建建议用 `buildx`：
```bash
# 登录仓库（Docker Hub / 私有 registry）
docker login <REGISTRY>

# 分别构建三镜像
docker build -t <REGISTRY>/ceron/python-svc:latest  -f backend/python-svc/Dockerfile  backend/python-svc
docker build -t <REGISTRY>/ceron/go-svc:latest      -f backend/go-svc/Dockerfile      backend/go-svc
docker build -t <REGISTRY>/ceron/frontend:latest    -f frontend/Dockerfile            frontend

# 推送
docker push <REGISTRY>/ceron/python-svc:latest
docker push <REGISTRY>/ceron/go-svc:latest
docker push <REGISTRY>/ceron/frontend:latest
```
推送后，把 `deploy/k8s/*-svc.yaml` 里的 `image:` 改为 `<REGISTRY>/ceron/...` 再 apply。

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

## 5. 方式三：Nginx 反向代理 + TLS

将 `deploy/nginx/ceron.conf` 放到对应位置并引用（upstream 指向实际运行地址，可为本机端口、容器名或 K8s Service 名）：

| OS | 放置 / 引用 | 校验与重载 |
|---|---|---|
| Linux | `/etc/nginx/sites-available/ceron.conf`，软链到 `sites-enabled/` | `sudo nginx -t && sudo systemctl reload nginx` |
| macOS | `/opt/homebrew/etc/nginx/servers/ceron.conf`（Apple Silicon）或 `/usr/local/etc/nginx/servers/`（Intel） | `nginx -t && brew services reload nginx` |
| Windows | `C:\nginx\conf\ceron.conf`，在 `nginx.conf` 的 `http{}` 内加 `include ceron.conf;` | `nginx -t && nginx -s reload` |

配置要点（见 `deploy/nginx/ceron.conf`）：
- `/` 反代到 frontend(:3000)；`/api`、`/v1`、`/gateway`、`/health`、`/docs`、`/openapi.json` 反代到 go-svc(:8080)。
- `client_max_body_size 25m` 支持保单/月结单扫描件上传；`proxy_read_timeout 120s` 容忍大模型流水线耗时。
- 默认 80→443 跳转；证书路径 `/etc/nginx/ssl/ceron.fullchain.pem` 与 `ceron.privkey.pem`，按需改为实际路径。
- Windows 下证书与站点文件用正斜杠或双反斜杠，例如 `C:/nginx/ssl/ceron.fullchain.pem`。

---

## 6. 方式四：Kubernetes

### 6.1 安装 kubectl（仅客户端）
```bash
# Windows
winget install Kubernetes.kubectl        # 或 choco install kubernetes-cli
# macOS
brew install kubectl
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -m 0755 kubectl /usr/local/bin/kubectl
```
并配置 `kubeconfig` 指向目标集群（有 ingress-nginx + 可选 cert-manager）。

### 6.2 准备配置
1. 编辑 `deploy/k8s/02-secret.yaml`，把 `LLM_API_KEY` 等替换为真实值（生产建议用 External Secrets / Sealed Secrets / Vault 注入，不要直接提交明文）。
2. 若用私有仓库，把 `10/11/12-*-svc.yaml` 中 `image:` 改为 `<REGISTRY>/ceron/...:latest`。

### 6.3 部署
```bash
# 用 kustomize 一次性应用（推荐）
kubectl apply -k deploy/k8s

# 或逐个文件
kubectl apply -f deploy/k8s/00-namespace.yaml \
             -f deploy/k8s/01-configmap.yaml \
             -f deploy/k8s/02-secret.yaml \
             -f deploy/k8s/10-python-svc.yaml \
             -f deploy/k8s/11-go-svc.yaml \
             -f deploy/k8s/12-frontend.yaml \
             -f deploy/k8s/20-ingress.yaml
```

### 6.4 验证
```bash
kubectl -n ceron get pods            # 三个服务均 Running
kubectl -n ceron get svc            # python-svc / go-svc / frontend ClusterIP
kubectl -n ceron get ingress        # ceron-ingress ADDRESS 已分配
kubectl -n ceron logs deploy/go-svc -f   # 观察启动与 /health
```

### 6.5 扩缩容与回滚
```bash
kubectl -n ceron scale deploy/go-svc --replicas=4
kubectl -n ceron rollout restart deploy/python-svc   # 配置/镜像更新后
kubectl -n ceron rollout status deploy/go-svc
kubectl -n ceron rollout undo deploy/go-svc         # 回滚到上一版本
```

---

## 7. 部署验证清单（通用）

1. `curl http://<python-svc>:8000/health` → `{"status":"ok","service":"intelligence",...}`
2. `curl http://<go-svc>:8080/health` → `{"status":"ok","service":"gateway"}`
3. `curl -X POST http://<go-svc>:8080/v1/intake -H "Content-Type: application/json" -d '{"vertical":"insurance_hk","text":"保單號：HK12345\n保額：800萬\n理賠金額：120萬\n資料完整度：0.9"}'` → 返回 job（completed）
4. 打开 frontend（或经 Nginx/Ingress 域名），提交表单，能看到处理结果。

---

## 8. 常见部署问题

| 现象 | 原因/处理 |
|---|---|
| go-svc 报连接 python 失败 | `PYTHON_SVC_URL` 未设或 python-svc 未启动；K8s 内应写为 `http://python-svc:8000` |
| 端口被占用（8000/8080/3000） | 杀掉占用进程或改端口（`GO_SVC_PORT`/compose ports） |
| mock 模式抽取不全 | 正常：正则兜底有限；配置 `LLM_API_KEY` 后由大模型抽取 |
| OCR/富集报「缺少配置」 | 对应 `OCR_PROVIDER`/`ENRICHMENT_PROVIDER` 的 URL/KEY 未配置 |
| Windows 下 go run 提示文件被占用 | 旧进程未退出：结束 `ceron-gateway.exe`/`go.exe` 后重试 |
| K8s Pod 一直 CrashLoopBackOff | 看 `kubectl -n ceron logs <pod>`；多为镜像拉取失败（需设 imagePullSecrets）或 `/health` 探针端口错 |
| Nginx 502 | upstream 地址不可达；确认 python-svc/go-svc 已起且防火墙放行对应端口 |
| Ingress 无外部 IP | ingress-nginx 控制器未装或 `ingressClassName: nginx` 不匹配 |
