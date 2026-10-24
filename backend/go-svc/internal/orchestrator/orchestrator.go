// Package orchestrator 文档处理流水线编排：收件 → 抽取 → 富集 → 决策 → 路由。
// 支持同步执行（Run）与异步执行（Submit + worker pool），完成后可回调 CRM 同步。
package orchestrator

import (
	"fmt"
	"sync"
	"time"

	"ceron-go/internal/client"
	"ceron-go/internal/queue"
)

// Job 表示一次文档处理作业。
type Job struct {
	ID        string                 `json:"id"`
	Vertical  string                 `json:"vertical"`
	Status    string                 `json:"status"` // queued | processing | completed | failed
	Result    map[string]interface{} `json:"result,omitempty"`
	Error     string                 `json:"error,omitempty"`
	CreatedAt time.Time              `json:"created_at"`
}

// Orchestrator 协调 Go 网关与 Python 智能服务。
type Orchestrator struct {
	Py   *client.PythonClient
	Pool *queue.Pool
	// OnComplete 在作业成功完成后回调（如 CRM 同步）；在独立 goroutine 中执行。
	OnComplete func(*Job)

	mu   sync.Mutex
	jobs map[string]*Job
}

// New 构造编排器。
func New(py *client.PythonClient) *Orchestrator {
	return &Orchestrator{Py: py, jobs: make(map[string]*Job)}
}

// Run 同步执行一次流水线（阻塞直至完成）。
func (o *Orchestrator) Run(id, vertical, text string) (*Job, error) {
	job := o.newJob(id, vertical)
	o.process(job, vertical, text)
	o.mu.Lock()
	defer o.mu.Unlock()
	if job.Status == "failed" {
		return job, fmt.Errorf("%s", job.Error)
	}
	return job, nil
}

// Submit 异步提交作业，立即返回（状态 queued）；未配置 Pool 时退化为同步。
func (o *Orchestrator) Submit(id, vertical, text string) *Job {
	job := o.newJob(id, vertical)
	if o.Pool == nil {
		o.process(job, vertical, text)
		return job
	}
	o.Pool.Submit(func() { o.process(job, vertical, text) })
	return job
}

func (o *Orchestrator) newJob(id, vertical string) *Job {
	job := &Job{ID: id, Vertical: vertical, Status: "queued", CreatedAt: time.Now()}
	o.mu.Lock()
	o.jobs[id] = job
	o.mu.Unlock()
	return job
}

func (o *Orchestrator) process(job *Job, vertical, text string) {
	o.mu.Lock()
	job.Status = "processing"
	o.mu.Unlock()

	res, err := o.Py.Pipeline(vertical, text)

	o.mu.Lock()
	if err != nil {
		job.Status = "failed"
		job.Error = err.Error()
	} else {
		job.Status = "completed"
		job.Result = res
	}
	o.mu.Unlock()

	if err == nil && o.OnComplete != nil {
		go o.OnComplete(job)
	}
}

// Get 获取作业状态。
func (o *Orchestrator) Get(id string) (*Job, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	job, ok := o.jobs[id]
	if !ok {
		return nil, fmt.Errorf("job %s not found", id)
	}
	return job, nil
}
