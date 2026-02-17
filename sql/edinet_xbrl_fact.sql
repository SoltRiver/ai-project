-- Formal DDL for edinet_xbrl_fact (PostgreSQL)
-- Phase 3 Requirement

CREATE TABLE IF NOT EXISTS edinet_xbrl_fact (
  id            bigserial PRIMARY KEY,
  doc_id        text NOT NULL REFERENCES edinet_documents(doc_id) ON DELETE CASCADE,
  concept       text NOT NULL,
  value_text    text,
  value_numeric numeric,
  unit_ref      text,
  decimals      text,
  period_start  date,
  period_end    date,
  instant_date  date,
  entity_id     text,
  context_ref   text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (
    doc_id, concept, context_ref, unit_ref,
    coalesce(value_text,''),
    coalesce(period_start::text,''),
    coalesce(period_end::text,''),
    coalesce(instant_date::text,'')
  )
);

CREATE INDEX IF NOT EXISTS idx_xbrl_fact_doc_concept ON edinet_xbrl_fact(doc_id, concept);
CREATE INDEX IF NOT EXISTS idx_xbrl_fact_concept     ON edinet_xbrl_fact(concept);
