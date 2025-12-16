-- 株価分析アシスタント データベースDDL
-- データ永続化用のテーブル定義

-- 銘柄マスタテーブル
CREATE TABLE IF NOT EXISTS stock_master (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    exchange VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'JPY',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sector (sector),
    INDEX idx_industry (industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 株価データテーブル（日次）
CREATE TABLE IF NOT EXISTS stock_prices_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(15, 2) NOT NULL,
    high_price DECIMAL(15, 2) NOT NULL,
    low_price DECIMAL(15, 2) NOT NULL,
    close_price DECIMAL(15, 2) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date (symbol, date),
    INDEX idx_date (date),
    INDEX idx_symbol (symbol),
    FOREIGN KEY (symbol) REFERENCES stock_master(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- テクニカル指標テーブル
CREATE TABLE IF NOT EXISTS technical_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    sma25 DECIMAL(15, 2),
    sma75 DECIMAL(15, 2),
    sma5 DECIMAL(15, 2),
    sma200 DECIMAL(15, 2),
    rsi DECIMAL(5, 2),
    macd DECIMAL(15, 2),
    macd_signal DECIMAL(15, 2),
    macd_histogram DECIMAL(15, 2),
    trend_slope DECIMAL(15, 6),
    trend_intercept DECIMAL(15, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date (symbol, date),
    INDEX idx_date (date),
    INDEX idx_symbol (symbol),
    FOREIGN KEY (symbol) REFERENCES stock_master(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ファンダメンタルデータテーブル
CREATE TABLE IF NOT EXISTS fundamental_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    per DECIMAL(10, 2),
    forward_pe DECIMAL(10, 2),
    pbr DECIMAL(10, 2),
    dividend_yield DECIMAL(5, 4),
    dividend_rate DECIMAL(15, 2),
    debt_to_equity DECIMAL(10, 2),
    return_on_equity DECIMAL(5, 4),
    return_on_assets DECIMAL(5, 4),
    profit_margin DECIMAL(5, 4),
    operating_margin DECIMAL(5, 4),
    current_ratio DECIMAL(10, 2),
    quick_ratio DECIMAL(10, 2),
    total_cash BIGINT,
    total_debt BIGINT,
    total_revenue BIGINT,
    revenue_growth DECIMAL(5, 4),
    earnings_growth DECIMAL(5, 4),
    market_cap BIGINT,
    enterprise_value BIGINT,
    book_value DECIMAL(15, 2),
    price_to_sales DECIMAL(10, 2),
    peg_ratio DECIMAL(10, 2),
    beta DECIMAL(5, 2),
    equity_ratio DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date (symbol, date),
    INDEX idx_date (date),
    INDEX idx_symbol (symbol),
    FOREIGN KEY (symbol) REFERENCES stock_master(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- AI分析結果テーブル
CREATE TABLE IF NOT EXISTS ai_analysis (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    analysis_date DATE NOT NULL,
    plus_factors TEXT,
    minus_factors TEXT,
    long_term_view TEXT,
    model_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_date (symbol, analysis_date),
    INDEX idx_date (analysis_date),
    FOREIGN KEY (symbol) REFERENCES stock_master(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ローソク足分類結果テーブル
CREATE TABLE IF NOT EXISTS candle_classification (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    candle_type VARCHAR(50),
    open_price DECIMAL(15, 2),
    high_price DECIMAL(15, 2),
    low_price DECIMAL(15, 2),
    close_price DECIMAL(15, 2),
    body_size DECIMAL(15, 2),
    upper_shadow DECIMAL(15, 2),
    lower_shadow DECIMAL(15, 2),
    is_bullish BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol_date (symbol, date),
    INDEX idx_date (date),
    INDEX idx_symbol (symbol),
    INDEX idx_candle_type (candle_type),
    FOREIGN KEY (symbol) REFERENCES stock_master(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ユーザー設定テーブル（将来拡張用）
CREATE TABLE IF NOT EXISTS user_settings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100),
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_key (user_id, setting_key),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ウォッチリストテーブル（将来拡張用）
CREATE TABLE IF NOT EXISTS watchlist (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_symbol (user_id, symbol),
    INDEX idx_user_id (user_id),
    INDEX idx_symbol (symbol),
    FOREIGN KEY (symbol) REFERENCES stock_master(symbol) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

