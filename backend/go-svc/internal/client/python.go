// Package client 调用 Python 智能服务层（Ceron Intelligence Service）的 REST 接口。
package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// PythonClient 封装对 Python 智能服务的 HTTP 调用。
type PythonClient struct {
	BaseURL string
	HTTP    *http.Client
}

// New 构造客户端，baseURL 形如 http://localhost:8000。
func New(baseURL string) *PythonClient {
	return &PythonClient{
		BaseURL: baseURL,
		HTTP:    &http.Client{Timeout: 60 * time.Second},
	}
}

type pipelineRequest struct {
	Vertical string `json:"vertical"`
	Text     string `json:"text"`
	Locale   string `json:"locale"`
}

// Pipeline 调用 /v1/pipeline，串联 抽取→富集→决策。
func (c *PythonClient) Pipeline(vertical, text, locale string) (map[string]interface{}, error) {
	body, err := json.Marshal(pipelineRequest{Vertical: vertical, Text: text, Locale: locale})
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequest(http.MethodPost, c.BaseURL+"/v1/pipeline", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("python svc returned %d: %s", resp.StatusCode, string(b))
	}

	var out map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}
	return out, nil
}
