
-- Derived Metrics Layer (Phase 8)
-- Stores calculated financial metrics with audit trail

CREATE TABLE IF NOT EXISTS edinet_financial_derived (
  id                  bigserial PRIMARY KEY,
  doc_id              text NOT NULL REFERENCES edinet_documents(doc_id) ON DELETE CASCADE,

  derived_key         text NOT NULL,      -- e.g. operating_margin, roe_end
  derived_label       text NOT NULL,

  value_numeric       numeric,

  period_type         text,
  duration_days       integer,

  source_metrics      jsonb NOT NULL,     -- List of source metric keys
  source_values       jsonb NOT NULL,     -- Detailed source values (value, unit, confidence)
  calculation_formula text NOT NULL,

  confidence          text,               -- HIGH/MID/LOW
  reason              text,               -- 1-line explanation

  variant_key         text,               -- For future extension (consolidated/annual)
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),

  UNIQUE (doc_id, derived_key)
);

CREATE INDEX IF NOT EXISTS idx_derived_doc ON edinet_financial_derived(doc_id);
