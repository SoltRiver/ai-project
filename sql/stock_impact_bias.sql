-- Stock News Table
CREATE TABLE IF NOT EXISTS stock_news (
    id SERIAL PRIMARY KEY,
    sec_code CHAR(5) NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    published_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_news_sec_code ON stock_news(sec_code);
CREATE INDEX IF NOT EXISTS idx_stock_news_published_at ON stock_news(published_at);

-- Stock News Analysis Table (Impact Classification)
CREATE TABLE IF NOT EXISTS stock_news_analysis (
    news_id INTEGER PRIMARY KEY REFERENCES stock_news(id) ON DELETE CASCADE,
    impact_type VARCHAR(20) NOT NULL CHECK (impact_type IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL')),
    impact_strength VARCHAR(10) NOT NULL CHECK (impact_strength IN ('HIGH', 'MEDIUM', 'LOW')),
    summary_2lines TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Stock Event Table
CREATE TABLE IF NOT EXISTS stock_event (
    id SERIAL PRIMARY KEY,
    sec_code CHAR(5) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- e.g. TOB, BUYBACK
    title TEXT NOT NULL,
    announced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_event_sec_code ON stock_event(sec_code);
CREATE INDEX IF NOT EXISTS idx_stock_event_announced_at ON stock_event(announced_at);

-- Stock Event Analysis Table (Impact Classification)
CREATE TABLE IF NOT EXISTS stock_event_analysis (
    event_id INTEGER PRIMARY KEY REFERENCES stock_event(id) ON DELETE CASCADE,
    impact_type VARCHAR(20) NOT NULL CHECK (impact_type IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL')),
    impact_strength VARCHAR(10) NOT NULL CHECK (impact_strength IN ('HIGH', 'MEDIUM', 'LOW')),
    summary_2lines TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
