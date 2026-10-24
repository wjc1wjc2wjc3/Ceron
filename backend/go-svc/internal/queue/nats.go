//go:build nats

package queue

import (
	"encoding/json"
	"strings"

	"github.com/nats-io/nats.go"
)

const (
	natsStreamName = "CERON_JOBS"
	natsSubject    = "ceron.jobs"
	natsConsumer   = "ceron-workers"
)

// NATSQueue 基于 NATS JetStream 的持久化异步队列，支持多实例水平扩展
// （同一 queue group 的多个消费者自动负载均衡，消息确认保证至少一次投递）。
// 仅在 `go build -tags nats` 时编译。
type NATSQueue struct {
	nc  *nats.Conn
	js  nats.JetStreamContext
	sub *nats.Subscription
}

// NewNATS 连接 NATS 并订阅作业主题；handler 在消息确认前被调用。
func NewNATS(url string, h Handler) (*NATSQueue, error) {
	nc, err := nats.Connect(url, nats.MaxReconnects(-1))
	if err != nil {
		return nil, err
	}
	js, err := nc.JetStream()
	if err != nil {
		return nil, err
	}
	// 幂等建流（已存在则忽略）
	if _, err := js.AddStream(&nats.StreamConfig{
		Name:     natsStreamName,
		Subjects: []string{natsSubject},
	}); err != nil && !strings.Contains(err.Error(), "already exists") {
		return nil, err
	}
	sub, err := js.QueueSubscribe(natsSubject, natsConsumer, func(m *nats.Msg) {
		var p struct {
			ID       string `json:"id"`
			Vertical string `json:"vertical"`
			Text     string `json:"text"`
		}
		if json.Unmarshal(m.Data, &p) == nil {
			h(p.ID, p.Vertical, p.Text)
		}
		_ = m.Ack()
	}, nats.Durable(natsConsumer), nats.ManualAck())
	if err != nil {
		return nil, err
	}
	return &NATSQueue{nc: nc, js: js, sub: sub}, nil
}

// NewQueue 在启用 nats 构建标签时返回 NATS 队列。
func NewQueue(url string, _ int, h Handler) (Queue, error) {
	return NewNATS(url, h)
}

// Submit 发布作业消息到 JetStream。
func (q *NATSQueue) Submit(id, vertical, text string) {
	b, _ := json.Marshal(struct {
		ID       string `json:"id"`
		Vertical string `json:"vertical"`
		Text     string `json:"text"`
	}{id, vertical, text})
	_, _ = q.js.Publish(natsSubject, b)
}

// Close 退订并断开连接。
func (q *NATSQueue) Close() {
	if q.sub != nil {
		_ = q.sub.Unsubscribe()
	}
	_ = q.nc.Drain()
}
