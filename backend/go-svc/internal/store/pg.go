//go:build postgres

package store

import (
	"database/sql"
	"encoding/json"
	"errors"

	"ceron-go/internal/orchestrator"
	_ "github.com/lib/pq"
)

// PGStore 是基于 PostgreSQL 的作业持久化实现（result 字段用 JSONB）。
// 仅在 `go build -tags postgres` 时编译。
type PGStore struct {
	db *sql.DB
}

const ddl = `
CREATE TABLE IF NOT EXISTS jobs (
  id         TEXT PRIMARY KEY,
  vertical   TEXT NOT NULL DEFAULT '',
  status     TEXT NOT NULL DEFAULT 'queued',
  result     JSONB,
  error      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);`

// ConnectPG 连接 Postgres 并自动建表（若尚未存在）。
func ConnectPG(url string) (*PGStore, error) {
	db, err := sql.Open("postgres", url)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	if _, err := db.Exec(ddl); err != nil {
		return nil, err
	}
	return &PGStore{db: db}, nil
}

// Kind 返回存储类型标识。
func (s *PGStore) Kind() string { return "postgres" }

// Upsert 插入或更新作业（以 ID 为主键，保留首次 created_at）。
func (s *PGStore) Upsert(j *orchestrator.Job) error {
	raw, _ := json.Marshal(j.Result)
	_, err := s.db.Exec(`
		INSERT INTO jobs (id, vertical, status, result, error, created_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (id) DO UPDATE SET
			vertical = EXCLUDED.vertical,
			status   = EXCLUDED.status,
			result   = EXCLUDED.result,
			error    = EXCLUDED.error`,
		j.ID, j.Vertical, j.Status, raw, j.Error, j.CreatedAt)
	return err
}

// Get 按 ID 获取作业。
func (s *PGStore) Get(id string) (*orchestrator.Job, error) {
	j := &orchestrator.Job{}
	var raw []byte
	err := s.db.QueryRow(
		`SELECT id, vertical, status, result, error, created_at FROM jobs WHERE id = $1`, id).
		Scan(&j.ID, &j.Vertical, &j.Status, &raw, &j.Error, &j.CreatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	if len(raw) > 0 {
		_ = json.Unmarshal(raw, &j.Result)
	}
	return j, nil
}

// List 返回最近 200 条作业（按创建时间倒序）。
func (s *PGStore) List() ([]*orchestrator.Job, error) {
	rows, err := s.db.Query(
		`SELECT id, vertical, status, result, error, created_at FROM jobs ORDER BY created_at DESC LIMIT 200`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]*orchestrator.Job, 0)
	for rows.Next() {
		j := &orchestrator.Job{}
		var raw []byte
		if err := rows.Scan(&j.ID, &j.Vertical, &j.Status, &raw, &j.Error, &j.CreatedAt); err != nil {
			return nil, err
		}
		if len(raw) > 0 {
			_ = json.Unmarshal(raw, &j.Result)
		}
		out = append(out, j)
	}
	return out, rows.Err()
}
