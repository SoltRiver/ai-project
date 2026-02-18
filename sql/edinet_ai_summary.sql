
-- AI Financial Summary Layer (Phase 10)
-- Stores rule-based generated summaries with strict evidence linking

CREATE TABLE IF NOT EXISTS edinet_ai_summary (
  id                bigserial PRIMARY KEY,
  sec_code          text NOT NULL,
  period_end_year   integer NOT NULL,
  kind              text NOT NULL,            -- 'SNAPSHOT' or 'DELTA'

  summary_text      text,                     -- The generated text
  bullet_points     jsonb,                    -- Extracted bullet points
  
  evidence          jsonb NOT NULL,           -- The SOURCE TRUTH (Facts + Selection Logic)
  input_hash        text NOT NULL,            -- SHA256 of canonical evidence for idempotency
  
  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now(),

  UNIQUE (sec_code, period_end_year, kind)
);

CREATE INDEX IF NOT EXISTS idx_ai_summary_sec ON edinet_ai_summary(sec_code);
