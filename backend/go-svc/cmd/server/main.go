// Ceron Go 网关/编排服务：高并发收件与流水线编排，调用 Python 智能服务层。
// 支持同步/异步作业、WhatsApp/企業微信 webhook 收件、CRM webhook 同步。
// 作业持久化：DATABASE_URL 设置时走 Postgres，否则内存；异步队列：NATS_URL 设置时走
// NATS JetStream，否则进程内 worker 池。
package main

import (
	"log"
	"net/http"
	"os"
	"strconv"

	"ceron-go/internal/client"
	"ceron-go/internal/connectors"
	"ceron-go/internal/handler"
	"ceron-go/internal/orchestrator"
	"ceron-go/internal/queue"
	"ceron-go/internal/store"
)

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			return n
		}
	}
	return fallback
}

func main() {
	// 默认 8001：8000 是 AiToken 后端（AiTokenWhole/AiTokenBackend）的端口，
	// 两者都绑 8000 时 Windows 上会静默共存（各占 127.0.0.1 / 0.0.0.0），
	// 更具体的 127.0.0.1 绑定会把请求抢走，导致 AiToken 前端登录 404 且无任何报错。
	pyURL := env("PYTHON_SVC_URL", "http://localhost:8001")
	port := env("GO_SVC_PORT", "8080")
	workers := envInt("WORKERS", 4)
	crmURL := os.Getenv("CRM_WEBHOOK_URL")
	dbURL := os.Getenv("DATABASE_URL")
	natsURL := os.Getenv("NATS_URL")

	py := client.New(pyURL)
	crm := connectors.New(crmURL)

	// —— 作业持久化层 ——
	st, err := store.Open(dbURL)
	if err != nil {
		log.Fatalf("store init failed: %v", err)
	}
	if st.Kind() == "postgres" {
		log.Printf("job store: postgres")
	} else {
		log.Printf("job store: memory (set DATABASE_URL to enable postgres)")
	}

	orc := orchestrator.New(py, st)

	// —— 异步队列层 ——
	q, err := queue.NewQueue(natsURL, workers, orc.Process)
	if err != nil {
		log.Fatalf("queue init failed: %v", err)
	}
	if natsURL != "" {
		log.Printf("queue: nats jetstream (%s)", natsURL)
	} else {
		log.Printf("queue: in-memory pool (workers=%d, set NATS_URL to enable jetstream)", workers)
	}
	orc.Queue = q

	orc.OnComplete = func(j *orchestrator.Job) {
		if err := crm.Sync(j); err != nil {
			log.Printf("crm sync failed for job %s: %v", j.ID, err)
		}
	}

	srv := handler.New(orc)
	mux := http.NewServeMux()
	srv.Register(mux)

	log.Printf("Ceron gateway listening on :%s, python svc=%s", port, pyURL)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
