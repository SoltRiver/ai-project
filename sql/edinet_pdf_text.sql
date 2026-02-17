
-- Phase 6: PDF Search System Tables

-- 1. Extraction Status (Idempotency & Quality)
CREATE TABLE IF NOT EXISTS edinet_pdf_extract_status (
    doc_id VARCHAR(8) PRIMARY KEY,
    status VARCHAR(10) NOT NULL, -- 'OK', 'NG', 'SKIP'
    page_count INTEGER,
    total_chars INTEGER,
    rule_version VARCHAR(10) DEFAULT 'v1',
    error_message TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pdf_status_doc FOREIGN KEY (doc_id) REFERENCES edinet_documents (doc_id)
);

-- 2. PDF Text Storage (Page Level)
CREATE TABLE IF NOT EXISTS edinet_pdf_text (
    doc_id VARCHAR(8) NOT NULL,
    page_no INTEGER NOT NULL,
    text_body TEXT, -- Normalized Text
    text_len INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (doc_id, page_no),
    CONSTRAINT fk_pdf_text_doc FOREIGN KEY (doc_id) REFERENCES edinet_documents (doc_id)
);

-- 3. Indexes (Phase 6: Hybrid Search)
-- Enable Extensions if not exists (Requires Superuser usually, assume available or skip)
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- CREATE EXTENSION IF NOT EXISTS btree_gin;

-- A. TRGM Index (Main Japanese Search)
-- CREATE INDEX idx_pdf_text_trgm ON edinet_pdf_text USING gin (text_body gin_trgm_ops);

-- B. FTS Index (Optional Alphanumeric)
-- ALTER TABLE edinet_pdf_text ADD COLUMN text_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', text_body)) STORED;
-- CREATE INDEX idx_pdf_text_fts ON edinet_pdf_text USING gin (text_tsv);

-- C. Metadata Indexes
CREATE INDEX IF NOT EXISTS idx_pdf_text_doc_id ON edinet_pdf_text (doc_id);
