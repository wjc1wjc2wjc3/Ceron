// Package queue 提供异步任务队列。Queue 接口同时由进程内 worker 池（Pool）
// 与 NATS JetStream（NATSQueue）实现；编排器只依赖接口，便于水平扩展。
package queue

import "sync"

// Handler 处理单个作业（由编排器注入 Process）。
type Handler func(jobID, vertical, text string)

// Queue 异步队列接口。Submit 立即返回，作业在后台 worker 中执行。
type Queue interface {
	Submit(jobID, vertical, text string)
	Close()
}

type taskItem struct {
	id, vertical, text string
	h                  Handler
}

// Pool 固定大小的进程内 worker 池（默认实现，无需外部依赖）。
type Pool struct {
	tasks   chan taskItem
	wg      sync.WaitGroup
	handler Handler
}

// NewPool 创建 workers 个 worker，buffer 为队列缓冲长度（背压用）。
func NewPool(workers, buffer int, h Handler) *Pool {
	if workers < 1 {
		workers = 1
	}
	if buffer < 1 {
		buffer = 16
	}
	p := &Pool{tasks: make(chan taskItem, buffer), handler: h}
	for i := 0; i < workers; i++ {
		p.wg.Add(1)
		go func() {
			defer p.wg.Done()
			for t := range p.tasks {
				t.h(t.id, t.vertical, t.text)
			}
		}()
	}
	return p
}

// Submit 提交任务；队列满时阻塞（背压），避免无限堆积。
func (p *Pool) Submit(id, vertical, text string) {
	p.tasks <- taskItem{id: id, vertical: vertical, text: text, h: p.handler}
}

// Close 停止接收并等待所有已提交任务完成。
func (p *Pool) Close() {
	close(p.tasks)
	p.wg.Wait()
}
