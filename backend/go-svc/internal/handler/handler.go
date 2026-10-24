// Package handler 暴露 HTTP 接口：文档收件（同步/异步）与作业查询。
package handler

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"ceron-go/internal/ingest"
	"ceron-go/internal/orchestrator"
)

// Server 持有编排器并注册路由。
type Server struct {
	O *orchestrator.Orchestrator
}

// New 构造 handler。
func New(o *orchestrator.Orchestrator) *Server {
	return &Server{O: o}
}

type intakeRequest struct {
	Vertical string `json:"vertical"`
	Text     string `json:"text"`
}

// Register 注册路由到给定的 ServeMux。
func (s *Server) Register(mux *http.ServeMux) {
	mux.HandleFunc("/v1/intake", s.Intake)
	mux.HandleFunc("/v1/intake/async", s.IntakeAsync)
	mux.HandleFunc("/v1/ingest/whatsapp", s.IngestWhatsApp)
	mux.HandleFunc("/v1/ingest/wecom", s.IngestWeCom)
	mux.HandleFunc("/v1/jobs", s.ListJobs)
	mux.HandleFunc("/v1/jobs/", s.GetJob)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "gateway"})
	})
}

// Intake 同步收件并等待流水线完成。
func (s *Server) Intake(w http.ResponseWriter, r *http.Request) {
	req, ok := decodeIntake(w, r)
	if !ok {
		return
	}
	id := newJobID()
	job, err := s.O.Run(id, req.Vertical, req.Text)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, job)
		return
	}
	writeJSON(w, http.StatusOK, job)
}

// IntakeAsync 异步收件：立即返回 queued 作业，用 /v1/jobs/{id} 轮询结果。
func (s *Server) IntakeAsync(w http.ResponseWriter, r *http.Request) {
	req, ok := decodeIntake(w, r)
	if !ok {
		return
	}
	job := s.O.Submit(newJobID(), req.Vertical, req.Text)
	writeJSON(w, http.StatusAccepted, job)
}

// IngestWhatsApp WhatsApp webhook 收件。
func (s *Server) IngestWhatsApp(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	msg, err := ingest.ParseWhatsApp(body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	job := s.O.Submit(newJobID(), msg.Vertical, msg.Text)
	writeJSON(w, http.StatusAccepted, job)
}

// IngestWeCom 企業微信回調收件。
func (s *Server) IngestWeCom(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	msg, err := ingest.ParseWeCom(body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	job := s.O.Submit(newJobID(), msg.Vertical, msg.Text)
	writeJSON(w, http.StatusAccepted, job)
}

// ListJobs 列出作业（看板数据源，支持持久化存储分页/恢复）。
func (s *Server) ListJobs(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	jobs, err := s.O.List()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{"jobs": jobs, "count": len(jobs)})
}

// GetJob 查询作业结果：/v1/jobs/{id}。
func (s *Server) GetJob(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/v1/jobs/")
	if id == "" {
		http.Error(w, "job id required", http.StatusBadRequest)
		return
	}
	job, err := s.O.Get(id)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}
	writeJSON(w, http.StatusOK, job)
}

func decodeIntake(w http.ResponseWriter, r *http.Request) (*intakeRequest, bool) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return nil, false
	}
	var req intakeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return nil, false
	}
	req.Vertical = strings.TrimSpace(req.Vertical)
	req.Text = strings.TrimSpace(req.Text)
	if req.Vertical == "" || req.Text == "" {
		http.Error(w, "vertical and text are required", http.StatusBadRequest)
		return nil, false
	}
	return &req, true
}

func newJobID() string {
	return fmt.Sprintf("job-%d", time.Now().UnixNano())
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
