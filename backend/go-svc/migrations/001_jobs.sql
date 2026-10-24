-- Ceron 作业表（Postgres）。store.ConnectPG 启动时也会自动执行此 DDL。
CREATE TABLE IF NOT EXISTS jobs (
  id         TEXT PRIMARY KEY,
  vertical   TEXT NOT NULL DEFAULT '',
  status     TEXT NOT NULL DEFAULT 'queued',
  result     JSONB,
  error      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at DESC);
