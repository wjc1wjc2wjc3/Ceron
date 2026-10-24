//go:build postgres

package store

import "ceron-go/internal/orchestrator"

// Open 根据 DATABASE_URL 选择存储；未设置时退化为内存，否则连接 Postgres。
func Open(url string) (orchestrator.JobStore, error) {
	if url == "" {
		return NewMemory(), nil
	}
	return ConnectPG(url)
}
