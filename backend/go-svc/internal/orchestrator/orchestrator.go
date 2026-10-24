// Package orchestrator 文档处理流水线编排：收件 → 抽取 → 富集 → 决策 → 路由。
// 支持同步执行（Run）与异步执行（Submit + 队列），完成后可回调 CRM 同步。
// 作业持久化通过 JobStore 接口（内存 / Postgres），队列通过 Queue 接口（进程池 / NATS）。
package orchestrator

import (
	"fmt"
	"sort"
	"sync"
	"time"

	"ceron-go/internal/client"
	"ceron-go/internal/queue"
)

// Job 表示一次文档处理作业。
type Job struct {
	ID           string                 `json:"id"`
	Vertical     string                 `json:"vertical"`
	Status       string                 `json:"status"` // queued | processing | completed | failed
	Result       map[string]interface{} `json:"result,omitempty"`
	Error        string                 `json:"error,omitempty"`
	ReviewStatus string                 `json:"review_status,omitempty"` // "" | approved | rejected
	ReviewNote   string                 `json:"review_note,omitempty"`
	ReviewedBy   string                 `json:"reviewed_by,omitempty"` // 审批人（默认 manual）
	ReviewedAt   time.Time              `json:"reviewed_at,omitempty"`
	CreatedAt    time.Time              `json:"created_at"`
}

// JobStore 作业持久化接口；实现见 internal/store（内存 / Postgres）。
type JobStore interface {
	Upsert(*Job) error
	Get(id string) (*Job, error)
	List(status string, limit, offset int) ([]*Job, error)
	Count(status string) (int, error)
	Kind() string // "memory" | "postgres"
}

// Orchestrator 协调 Go 网关与 Python 智能服务。
type Orchestrator struct {
	Py   *client.PythonClient
	Store JobStore
	Queue queue.Queue
	// PipelineFn 可覆盖默认 Python 调用（测试桩用）；为 nil 时调用 Py.Pipeline。
	PipelineFn func(vertical, text string) (map[string]interface{}, error)
	// OnComplete 在作业成功完成后回调（如 CRM 同步）；在独立 goroutine 中执行。
	OnComplete func(*Job)

	mu   sync.Mutex
	jobs map[string]*Job // 内存缓存，便于无 DB 时快速查询
}

// New 构造编排器；store 为 nil 时退化为纯内存。
func New(py *client.PythonClient, store JobStore) *Orchestrator {
	return &Orchestrator{Py: py, Store: store, jobs: make(map[string]*Job)}
}

func (o *Orchestrator) pipeline(vertical, text string) (map[string]interface{}, error) {
	if o.PipelineFn != nil {
		return o.PipelineFn(vertical, text)
	}
	return o.Py.Pipeline(vertical, text)
}

// Run 同步执行一次流水线（阻塞直至完成）。
func (o *Orchestrator) Run(id, vertical, text string) (*Job, error) {
	job := o.newJob(id, vertical)
	o.Process(id, vertical, text)
	if job.Status == "failed" {
		return job, fmt.Errorf("%s", job.Error)
	}
	return job, nil
}

// Submit 异步提交作业，立即返回（状态 queued）；未配置 Queue 时退化为同步。
func (o *Orchestrator) Submit(id, vertical, text string) *Job {
	job := o.newJob(id, vertical)
	if o.Queue == nil {
		o.Process(id, vertical, text)
	} else {
		o.Queue.Submit(id, vertical, text)
	}
	return job
}

func (o *Orchestrator) newJob(id, vertical string) *Job {
	job := &Job{ID: id, Vertical: vertical, Status: "queued", CreatedAt: time.Now()}
	o.persist(job)
	return job
}

func (o *Orchestrator) persist(job *Job) {
	if o.Store != nil {
		_ = o.Store.Upsert(job)
	}
	o.mu.Lock()
	o.jobs[job.ID] = job
	o.mu.Unlock()
}

// Process 执行单个作业的流水线（供同步调用、进程池 worker 或 NATS 消费者复用）。
func (o *Orchestrator) Process(jobID, vertical, text string) {
	o.mu.Lock()
	job := o.jobs[jobID]
	o.mu.Unlock()
	if job == nil {
		return
	}

	job.Status = "processing"
	o.persist(job)

	res, err := o.pipeline(vertical, text)
	if err != nil {
		job.Status = "failed"
		job.Error = err.Error()
	} else {
		job.Status = "completed"
		job.Result = res
	}
	o.persist(job)

	if err == nil && o.OnComplete != nil {
		go o.OnComplete(job)
	}
}

// Get 获取作业状态（优先持久化存储）。
func (o *Orchestrator) Get(id string) (*Job, error) {
	if o.Store != nil {
		if j, err := o.Store.Get(id); err == nil {
			return j, nil
		}
	}
	o.mu.Lock()
	defer o.mu.Unlock()
	job, ok := o.jobs[id]
	if !ok {
		return nil, fmt.Errorf("job %s not found", id)
	}
	return job, nil
}

// List 返回作业列表（按状态过滤 + 分页；优先持久化存储，支持重启后恢复），并返回符合条件的总数。
func (o *Orchestrator) List(status string, limit, offset int) ([]*Job, int, error) {
	if o.Store != nil {
		jobs, err := o.Store.List(status, limit, offset)
		if err != nil {
			return nil, 0, err
		}
		total, err := o.Store.Count(status)
		if err != nil {
			return nil, 0, err
		}
		return jobs, total, nil
	}
	o.mu.Lock()
	defer o.mu.Unlock()
	all := make([]*Job, 0, len(o.jobs))
	for _, j := range o.jobs {
		if status == "" || j.Status == status {
			all = append(all, j)
		}
	}
	sort.SliceStable(all, func(i, k int) bool { return all[i].CreatedAt.After(all[k].CreatedAt) })
	if offset < 0 {
		offset = 0
	}
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	if offset > len(all) {
		return []*Job{}, 0, nil
	}
	end := offset + limit
	if end > len(all) {
		end = len(all)
	}
	return all[offset:end], len(all), nil
}

// SetReview 记录人工审批结论（approved/rejected）与审计信息，持久化并返回更新后的作业。
// 支持作业不在内存缓存时回源持久化存储。reviewer 为空时记为 "manual"。
func (o *Orchestrator) SetReview(id, status, note, reviewer string) (*Job, error) {
	if status != "approved" && status != "rejected" {
		return nil, fmt.Errorf("invalid review status: %s", status)
	}
	o.mu.Lock()
	job := o.jobs[id]
	o.mu.Unlock()
	if job == nil && o.Store != nil {
		if j, err := o.Store.Get(id); err == nil {
			job = j
			o.mu.Lock()
			o.jobs[id] = j
			o.mu.Unlock()
		}
	}
	if job == nil {
		return nil, fmt.Errorf("job %s not found", id)
	}
	if reviewer == "" {
		reviewer = "manual"
	}
	job.ReviewStatus = status
	job.ReviewNote = note
	job.ReviewedBy = reviewer
	job.ReviewedAt = time.Now().UTC()
	o.persist(job)
	return job, nil
}
