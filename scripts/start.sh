#!/usr/bin/env bash
# Ceron 一键本地启动（macOS / Linux）
# 依次拉起：python-svc(8001) → go-svc(8080) → frontend(3000)，Ctrl+C 一键停止全部。
# 用法：
#   ./scripts/start.sh           # 首次会创建 venv 并安装依赖、npm install
#   ./scripts/start.sh --skip-install   # 跳过依赖安装
#   ./scripts/start.sh --no-browser    # 不自动打开浏览器
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY_DIR="$ROOT/backend/python-svc"
GO_DIR="$ROOT/backend/go-svc"
FE_DIR="$ROOT/frontend"
# 8001 而非 8000：8000 是 AiToken 后端（AiTokenWhole/AiTokenBackend）的端口，
# 两者都绑 8000 时 Windows 上会静默共存（各占 127.0.0.1 / 0.0.0.0），
# 更具体的 127.0.0.1 绑定会把请求抢走，导致 AiToken 前端登录 404 且无任何报错。
PY_PORT=8001
GO_PORT=8080
FE_PORT=3000

SKIP_INSTALL=0
NO_BROWSER=0
for a in "$@"; do
  case "$a" in
    --skip-install) SKIP_INSTALL=1 ;;
    --no-browser)   NO_BROWSER=1 ;;
  esac
done

export PYTHON_SVC_URL="http://localhost:$PY_PORT"
export GO_SVC_PORT="$GO_PORT"

LOG_DIR="$ROOT/logs"; mkdir -p "$LOG_DIR"
PIDS=()

cleanup() {
  echo ""
  echo "[ceron] 停止所有服务…"
  for pid in "${PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null
  done
  # 同时清理可能的子进程（uvicorn --reload / npm）
  pkill -f "uvicorn app.main:app" 2>/dev/null || true
  pkill -f "go run ./cmd/server"  2>/dev/null || true
  pkill -f "next dev"             2>/dev/null || true
  wait 2>/dev/null || true
  echo "[ceron] 已停止。"
}
trap cleanup INT TERM

# —— 1. Python 智能层 ——
echo "[ceron] 启动 python-svc :$PY_PORT …"
(
  cd "$PY_DIR" || exit 1
  if [ ! -d .venv ]; then
    [ "$SKIP_INSTALL" -eq 0 ] && python3 -m venv .venv
  fi
  if [ "$SKIP_INSTALL" -eq 0 ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate 2>/dev/null || true
    pip install -q -r requirements.txt 2>/dev/null || true
  fi
  exec uvicorn app.main:app --host 0.0.0.0 --port "$PY_PORT" --reload
) >"$LOG_DIR/py.log" 2>&1 &
PIDS+=($!)

# —— 2. Go 网关 ——
echo "[ceron] 启动 go-svc :$GO_PORT …"
( cd "$GO_DIR" && exec go run ./cmd/server ) >"$LOG_DIR/go.log" 2>&1 &
PIDS+=($!)

# —— 3. 前端 ——
echo "[ceron] 启动 frontend :$FE_PORT …"
(
  cd "$FE_DIR" || exit 1
  if [ "$SKIP_INSTALL" -eq 0 ] && [ ! -d node_modules ]; then
    npm install >/dev/null 2>&1
  fi
  exec npm run dev
) >"$LOG_DIR/fe.log" 2>&1 &
PIDS+=($!)

# 健康检查
echo "[ceron] 等待服务就绪…"
py_ok=0; go_ok=0
for i in $(seq 1 30); do
  if [ "$py_ok" -eq 0 ]; then
    curl -sf "http://localhost:$PY_PORT/health" >/dev/null && { py_ok=1; echo "  ✓ python-svc 就绪"; }
  fi
  if [ "$go_ok" -eq 0 ]; then
    curl -sf "http://localhost:$GO_PORT/health" >/dev/null && { go_ok=1; echo "  ✓ go-svc 就绪"; }
  fi
  [ "$py_ok" -eq 1 ] && [ "$go_ok" -eq 1 ] && break
  sleep 1
done

echo ""
echo "[ceron] 已全部启动。前端 http://localhost:$FE_PORT   (Ctrl+C 停止)"
echo "[ceron]   日志目录: $LOG_DIR"

if [ "$NO_BROWSER" -eq 0 ] && command -v xdg-open >/dev/null 2>&1; then
  sleep 3; xdg-open "http://localhost:$FE_PORT" >/dev/null 2>&1 || true
elif [ "$NO_BROWSER" -eq 0 ] && command -v open >/dev/null 2>&1; then
  sleep 3; open "http://localhost:$FE_PORT" >/dev/null 2>&1 || true
fi

wait
