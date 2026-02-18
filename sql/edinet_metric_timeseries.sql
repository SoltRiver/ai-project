
-- Timeseries & Comparison Layer (Phase 9)
-- Safe Fiscal Year Comparison with Audit Trail

-- 1. Representative Timeseries Table
-- Stores the "Best" value for a specific fiscal year (period_end_year)
CREATE TABLE IF NOT EXISTS edinet_metric_timeseries (
  id                bigserial PRIMARY KEY,
  sec_code          text NOT NULL,
  metric_key        text NOT NULL,
  period_end_year   integer NOT NULL,         -- Calendar year of period end
  fiscal_year_label text NOT NULL,            -- e.g. "2023" (FY2023)

  doc_id            text NOT NULL REFERENCES edinet_documents(doc_id),
  
  value_numeric     numeric NOT NULL,
  period_type       text NOT NULL,            -- duration/instant
  duration_days     integer,                  -- 300-400 for annual duration

  selection_notes   jsonb NOT NULL,           -- Why this doc was selected
  
  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now(),

  UNIQUE (sec_code, metric_key, period_end_year)
);

CREATE INDEX IF NOT EXISTS idx_timeseries_sec ON edinet_metric_timeseries(sec_code);
CREATE INDEX IF NOT EXISTS idx_timeseries_metric ON edinet_metric_timeseries(metric_key);


-- 2. Comparison Table
-- Stores calculated growth and trends
CREATE TABLE IF NOT EXISTS edinet_metric_comparison (
  id                bigserial PRIMARY KEY,
  sec_code          text NOT NULL,
  metric_key        text NOT NULL,
  period_end_year   integer NOT NULL,         -- Current Year
  
  doc_id            text NOT NULL REFERENCES edinet_documents(doc_id), -- Source of Current Year

  yoy_abs           numeric,
  yoy_pct           numeric,
  turnaround_flag   text,                     -- NONE / NEG_TO_POS / POS_TO_NEG

  cagr_3y           numeric,
  cagr_5y           numeric,

  trend_label       text,                     -- UP/DOWN/FLAT/VOLATILE
  trend_reason      text,

  source_docs       jsonb NOT NULL,           -- List of doc_ids used for calculation (Past years)
  calc_notes        jsonb NOT NULL,           -- Calculation details (missing prev, excluded outliers)

  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now(),

  UNIQUE (sec_code, metric_key, period_end_year)
);

CREATE INDEX IF NOT EXISTS idx_comparison_sec ON edinet_metric_comparison(sec_code);
