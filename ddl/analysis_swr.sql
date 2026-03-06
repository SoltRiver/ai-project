-- =========================================
-- AI分析SWRシステム用テーブル定義（PostgreSQL）
-- 事前生成 + 定期差分更新 + SWR表示パターン
-- =========================================

-- 1) analysis_snapshot: 表示用の最新スナップショット
CREATE TABLE IF NOT EXISTS analysis_snapshot (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    asof_ts TIMESTAMPTZ NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ttl_sec INTEGER NOT NULL DEFAULT 3600,
    status VARCHAR(20) NOT NULL DEFAULT 'ok',
    content_md TEXT NOT NULL DEFAULT '',
    input_hash VARCHAR(64) NOT NULL DEFAULT '',
    model_version VARCHAR(50) NOT NULL DEFAULT '',
    prompt_version VARCHAR(50) NOT NULL DEFAULT '',
    last_error_code VARCHAR(50),
    last_error_message TEXT,

    -- 銘柄×分析タイプで一意
    CONSTRAINT uq_snapshot_stock_type UNIQUE (stock_code, analysis_type)
);

-- スナップショット検索用インデックス
CREATE INDEX IF NOT EXISTS ix_snapshot_type_generated
    ON analysis_snapshot (analysis_type, generated_at DESC);
CREATE INDEX IF NOT EXISTS ix_snapshot_status
    ON analysis_snapshot (status);

-- 2) analysis_job: ジョブキュー
CREATE TABLE IF NOT EXISTS analysis_job (
    job_id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    reason VARCHAR(50) NOT NULL DEFAULT 'ttl',
    desired_asof_ts TIMESTAMPTZ NOT NULL,
    desired_input_hash VARCHAR(64) NOT NULL,
    dedupe_key VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    locked_by VARCHAR(100),
    locked_until TIMESTAMPTZ,
    last_error_code VARCHAR(50),
    last_error_message TEXT,

    -- 重複排除キーの一意制約
    CONSTRAINT uq_job_dedupe_key UNIQUE (dedupe_key)
);

-- ジョブキュー検索用インデックス（ステータス→優先度高い順→投入時刻順）
CREATE INDEX IF NOT EXISTS ix_job_queue
    ON analysis_job (status, priority DESC, queued_at ASC);
-- ロック期限切れ検出用
CREATE INDEX IF NOT EXISTS ix_job_locked_until
    ON analysis_job (locked_until);

-- 3) analysis_config: 運用調整用設定テーブル
CREATE TABLE IF NOT EXISTS analysis_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL
);

-- 初期設定データ投入（既存の場合はスキップ）
INSERT INTO analysis_config (key, value) VALUES
    ('TH_PRICE_PCT', '1.5'),
    ('TH_VOL_RATIO', '2.0'),
    ('TTL_INTRADAY_SEC', '3600'),
    ('TTL_DAILY_SEC', '86400'),
    ('WORKER_LOCK_SEC', '120'),
    ('MAX_ATTEMPTS', '3'),
    ('CIRCUIT_BREAKER_THRESHOLD', '10'),
    ('CIRCUIT_BREAKER_COOLDOWN_SEC', '300')
ON CONFLICT (key) DO NOTHING;
