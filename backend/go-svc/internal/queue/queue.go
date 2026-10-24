// Package queue 提供进程内异步任务队列（固定 worker 池）。
// 生产环境可替换为 NATS/Kafka 消费者组，Submit(Task) 接口保持不变。
package queue

import "sync"

// Task 是一个可执行任务。
type Task func()

// Pool 固定大小的 worker 池。
type Pool struct {
	tasks chan Task
	wg    sync.WaitGroup
}

// NewPool 创建 workers 个 worker，buffer 为队列缓冲长度（背压用）。
func NewPool(workers, buffer int) *Pool {
	if workers < 1 {
		workers = 1
	}
	if buffer < 1 {
		buffer = 16
	}
	p := &Pool{tasks: make(chan Task, buffer)}
	for i := 0; i < workers; i++ {
		p.wg.Add(1)
		go func() {
			defer p.wg.Done()
			for t := range p.tasks {
				t()
			}
		}()
	}
	return p
}

// Submit 提交任务；队列满时阻塞（背压），避免无限堆积。
func (p *Pool) Submit(t Task) { p.tasks <- t }

// Close 停止接收并等待所有已提交任务完成。
func (p *Pool) Close() { close(p.tasks); p.wg.Wait() }
