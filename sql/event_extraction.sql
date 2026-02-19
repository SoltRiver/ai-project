-- ============================================================
-- イベント自動抽出用スキーマ
-- ============================================================

-- ソース管理テーブル（合法性強制チェック）
CREATE TABLE IF NOT EXISTS event_source_policy (
    source_name        TEXT PRIMARY KEY,
    -- ソースの種別: EDINET_API / RSS / MANUAL / TDNET_API
    source_type        TEXT NOT NULL,
    -- 法的根拠: Official API / Official RSS / Manual / Paid API
    legal_basis        TEXT NOT NULL,
    -- 利用規約URL
    terms_url          TEXT,
    -- robots.txt URL
    robots_url         TEXT,
    -- 自動取得許可フラグ
    auto_fetch_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    -- 確認日時
    checked_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 承認者
    approved_by        TEXT NOT NULL DEFAULT 'SYSTEM',
    -- 有効期限（checked_at + 180日を推奨）
    expires_at         TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 冪等管理テーブル（日付単位の取得状態）
CREATE TABLE IF NOT EXISTS event_ingest_state (
    -- ソース名（event_source_policyと紐づく）
    source_name    TEXT NOT NULL,
    -- 巡回日付（YYYY-MM-DD）
    ingest_date    DATE NOT NULL,
    -- 処理状態: PENDING / PROCESSING / DONE / ERROR
    status         TEXT NOT NULL DEFAULT 'PENDING',
    -- 取得件数
    fetched_count  INTEGER DEFAULT 0,
    -- 抽出件数
    extracted_count INTEGER DEFAULT 0,
    -- エラーメッセージ
    error_message  TEXT,
    -- 処理開始日時
    started_at     TIMESTAMP WITH TIME ZONE,
    -- 処理完了日時
    completed_at   TIMESTAMP WITH TIME ZONE,
    -- 作成日時
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_name, ingest_date)
);

-- stock_event テーブルへの追加カラム（既存テーブルの拡張）
-- ※ SQLAlchemy create_all で自動反映されるため、ALTER TABLE は参考用
-- ALTER TABLE stock_event ADD COLUMN IF NOT EXISTS doc_id TEXT;
-- ALTER TABLE stock_event ADD COLUMN IF NOT EXISTS source_name TEXT DEFAULT 'MANUAL';
-- ALTER TABLE stock_event ADD COLUMN IF NOT EXISTS extraction_method TEXT DEFAULT 'MANUAL';

-- 重複防止インデックス（doc_id + event_type で冪等）
CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_event_doc_event
    ON stock_event(doc_id, event_type) WHERE doc_id IS NOT NULL;
