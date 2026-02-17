-- Formal DDL for edinet_financial_highlight (PostgreSQL)
-- Phase 4 Requirement: Safe Design

CREATE TABLE IF NOT EXISTS edinet_financial_highlight (
  id                bigserial PRIMARY KEY,
  doc_id            text NOT NULL REFERENCES edinet_documents(doc_id) ON DELETE CASCADE,

  metric_key        text NOT NULL,
  metric_label      text NOT NULL,

  selected_fact_id  bigint REFERENCES edinet_xbrl_fact(id),

  scope             text DEFAULT 'unknown',   -- consolidated/non_consolidated/unknown
  period_type       text DEFAULT 'unknown',   -- duration/instant/unknown
  duration_days     integer,

  period_start      date,
  period_end        date,

  value_numeric     numeric,
  raw_value_text    text,                     -- Required (keep even if numeric conversion fails)
  unit_label        text,
  source_concept    text,

  confidence        text,                     -- HIGH/MID/LOW
  reason            text,                     -- 1-line description

  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),

  UNIQUE (doc_id, metric_key)
);

CREATE INDEX IF NOT EXISTS idx_highlight_doc    ON edinet_financial_highlight(doc_id);
CREATE INDEX IF NOT EXISTS idx_highlight_metric ON edinet_financial_highlight(metric_key);
