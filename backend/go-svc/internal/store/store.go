// Package store 提供作业持久化。JobStore 接口由 Postgres 与内存两种实现满足，
// 编排器（orchestrator）依赖接口而非具体实现，默认无 DATABASE_URL 时退化为内存。
package store

import (
	"errors"
	"sort"
	"sync"

	"ceron-go/internal/orchestrator"
)

// ErrNotFound 表示作业不存在。
var ErrNotFound = errors.New("job not found")

// MemoryStore 是 JobStore 的内存实现，用于开发/测试与无数据库兜底。
type MemoryStore struct {
	mu   sync.Mutex
	jobs map[string]*orchestrator.Job
}

// NewMemory 构造内存存储。
func NewMemory() *MemoryStore {
	return &MemoryStore{jobs: make(map[string]*orchestrator.Job)}
}

// Kind 返回存储类型标识。
func (s *MemoryStore) Kind() string { return "memory" }

// Upsert 插入或更新作业（以 ID 为主键）。
func (s *MemoryStore) Upsert(j *orchestrator.Job) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.jobs[j.ID] = j
	return nil
}

// Get 按 ID 获取作业。
func (s *MemoryStore) Get(id string) (*orchestrator.Job, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	j, ok := s.jobs[id]
	if !ok {
		return nil, ErrNotFound
	}
	return j, nil
}

// List 按状态过滤 + 分页返回作业（按创建时间倒序）；limit<=0 或 >200 取 50，offset<0 取 0。
func (s *MemoryStore) List(status string, limit, offset int) ([]*orchestrator.Job, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	all := make([]*orchestrator.Job, 0, len(s.jobs))
	for _, j := range s.jobs {
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
		return []*orchestrator.Job{}, nil
	}
	end := offset + limit
	if end > len(all) {
		end = len(all)
	}
	return all[offset:end], nil
}

// Count 返回符合过滤条件的作业总数。
func (s *MemoryStore) Count(status string) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if status == "" {
		return len(s.jobs), nil
	}
	c := 0
	for _, j := range s.jobs {
		if j.Status == status {
			c++
		}
	}
	return c, nil
}
