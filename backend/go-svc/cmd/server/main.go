// Ceron Go 网关/编排服务：高并发收件与流水线编排，调用 Python 智能服务层。
// 支持同步/异步作业、WhatsApp/企業微信 webhook 收件、CRM webhook 同步。
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
	pyURL := env("PYTHON_SVC_URL", "http://localhost:8000")
	port := env("GO_SVC_PORT", "8080")
	workers := envInt("WORKERS", 4)
	crmURL := os.Getenv("CRM_WEBHOOK_URL")

	py := client.New(pyURL)
	pool := queue.NewPool(workers, 256)
	crm := connectors.New(crmURL)

	orc := orchestrator.New(py)
	orc.Pool = pool
	orc.OnComplete = func(j *orchestrator.Job) {
		if err := crm.Sync(j); err != nil {
			log.Printf("crm sync failed for job %s: %v", j.ID, err)
		}
	}

	srv := handler.New(orc)

	mux := http.NewServeMux()
	srv.Register(mux)

	log.Printf("Ceron gateway listening on :%s, python svc=%s, workers=%d, crm=%s",
		port, pyURL, workers, crmURL)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
