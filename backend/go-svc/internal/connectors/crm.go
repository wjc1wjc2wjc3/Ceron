// Package connectors 将处理完成的作业同步到外部系统（CRM / 港式核心系统）。
// 当前为 webhook 实现；生产可替换为 Salesforce/Dynamics SDK 或消息队列消费者。
package connectors

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"ceron-go/internal/orchestrator"
)

// CRM 通过 webhook 推送作业结果。
type CRM struct {
	WebhookURL string
	HTTP       *http.Client
}

// New 构造 CRM 连接器；webhookURL 为空时 Sync 为 no-op。
func New(webhookURL string) *CRM {
	return &CRM{WebhookURL: webhookURL, HTTP: &http.Client{Timeout: 15 * time.Second}}
}

// Sync 推送作业结果到 CRM webhook。
func (c *CRM) Sync(job *orchestrator.Job) error {
	if c.WebhookURL == "" || job == nil {
		return nil
	}
	body, err := json.Marshal(map[string]interface{}{"event": "job.completed", "job": job})
	if err != nil {
		return err
	}
	resp, err := c.HTTP.Post(c.WebhookURL, "application/json", bytes.NewReader(body))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("crm webhook returned %d", resp.StatusCode)
	}
	return nil
}
