//go:build postgres

package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"strconv"

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
  id            TEXT PRIMARY KEY,
  vertical      TEXT NOT NULL DEFAULT '',
  status        TEXT NOT NULL DEFAULT 'queued',
  result        JSONB,
  error         TEXT,
  review_status TEXT NOT NULL DEFAULT '',
  review_note   TEXT,
  reviewed_by   TEXT NOT NULL DEFAULT '',
  reviewed_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
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
		INSERT INTO jobs (id, vertical, status, result, error, review_status, review_note, reviewed_by, reviewed_at, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		ON CONFLICT (id) DO UPDATE SET
			vertical      = EXCLUDED.vertical,
			status        = EXCLUDED.status,
			result        = EXCLUDED.result,
			error         = EXCLUDED.error,
			review_status = EXCLUDED.review_status,
			review_note   = EXCLUDED.review_note,
			reviewed_by   = EXCLUDED.reviewed_by,
			reviewed_at   = EXCLUDED.reviewed_at`,
		j.ID, j.Vertical, j.Status, raw, j.Error, j.ReviewStatus, j.ReviewNote, j.ReviewedBy, j.ReviewedAt, j.CreatedAt)
	return err
}

// Get 按 ID 获取作业。
func (s *PGStore) Get(id string) (*orchestrator.Job, error) {
	j := &orchestrator.Job{}
	var raw []byte
	err := s.db.QueryRow(
		`SELECT id, vertical, status, result, error, review_status, review_note, reviewed_by, reviewed_at, created_at FROM jobs WHERE id = $1`, id).
		Scan(&j.ID, &j.Vertical, &j.Status, &raw, &j.Error, &j.ReviewStatus, &j.ReviewNote, &j.ReviewedBy, &j.ReviewedAt, &j.CreatedAt)
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

// List 按状态过滤 + 分页返回作业（按创建时间倒序）。
func (s *PGStore) List(status string, limit, offset int) ([]*orchestrator.Job, error) {
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	if offset < 0 {
		offset = 0
	}
	query := `SELECT id, vertical, status, result, error, review_status, review_note, reviewed_by, reviewed_at, created_at FROM jobs`
	args := []interface{}{}
	if status != "" {
		query += ` WHERE status = $1`
		args = append(args, status)
	}
	query += ` ORDER BY created_at DESC LIMIT ` + strconv.Itoa(limit) + ` OFFSET ` + strconv.Itoa(offset)
	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]*orchestrator.Job, 0)
	for rows.Next() {
		j := &orchestrator.Job{}
		var raw []byte
		if err := rows.Scan(&j.ID, &j.Vertical, &j.Status, &raw, &j.Error, &j.ReviewStatus, &j.ReviewNote, &j.ReviewedBy, &j.ReviewedAt, &j.CreatedAt); err != nil {
			return nil, err
		}
		if len(raw) > 0 {
			_ = json.Unmarshal(raw, &j.Result)
		}
		out = append(out, j)
	}
	return out, rows.Err()
}

// Count 返回符合过滤条件的作业总数。
func (s *PGStore) Count(status string) (int, error) {
	if status == "" {
		var n int
		err := s.db.QueryRow(`SELECT count(*) FROM jobs`).Scan(&n)
		return n, err
	}
	var n int
	err := s.db.QueryRow(`SELECT count(*) FROM jobs WHERE status = $1`, status).Scan(&n)
	return n, err
}
