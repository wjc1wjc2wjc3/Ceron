//go:build !nats

package queue

import "errors"

// NewQueue 在未启用 nats 标签时始终返回进程内 worker 池；传入 url 则提示需重新编译。
func NewQueue(url string, workers int, h Handler) (Queue, error) {
	if url != "" {
		return nil, errors.New("nats support not compiled in; rebuild with `-tags nats`")
	}
	return NewPool(workers, 256, h), nil
}
