//go:build !postgres

package store

import (
	"fmt"

	"ceron-go/internal/orchestrator"
)

// Open 根据 DATABASE_URL 选择存储；未设置或本构建未含 postgres 时退化为内存。
func Open(url string) (orchestrator.JobStore, error) {
	if url == "" {
		return NewMemory(), nil
	}
	return nil, fmt.Errorf("postgres support not compiled in; rebuild with `-tags postgres`")
}
